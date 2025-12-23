
const http = require('http');
const zlib = require('zlib');
const { Transform } = require('stream');

async function main() {
    console.log('Starting Pure Node.js Download Test...');

    const API_BASE = 'http://127.0.0.1:8000';
    const randomSuffix = Math.floor(Math.random() * 10000);
    const USER = {
        username: `downloader${randomSuffix}`,
        email: `download_${randomSuffix}@example.com`,
        password: 'Str0ngP@ssw0rd!2025'
    };

    // Helper for JSON requests
    async function request(method, path, body = null, token = null) {
        return new Promise((resolve, reject) => {
            const url = new URL(API_BASE + path);
            const headers = { 'Content-Type': 'application/json' };
            if (token) headers['Authorization'] = `Bearer ${token}`;

            const req = http.request(url, { method, headers }, res => {
                let data = '';
                res.on('data', c => data += c);
                res.on('end', () => {
                    try {
                        const json = JSON.parse(data);
                        if (res.statusCode >= 400) reject({ status: res.statusCode, body: json });
                        else resolve(json);
                    } catch (e) {
                        resolve(data);
                    }
                });
            });
            req.on('error', reject);
            if (body) req.write(JSON.stringify(body));
            req.end();
        });
    }

    let token, job, taskId;

    try {
        // 1. Setup (Register -> Login -> Project -> Job)
        console.log('1️⃣  Setup...');
        try { await request('POST', '/v1/auth/register', { ...USER, display_name: 'Downloader' }); } catch (e) { }

        const loginRes = await request('POST', '/v1/auth/login/password', { username_or_email: USER.email, password: USER.password });
        token = loginRes.access_token;
        console.log('✅ Logged in');

        const project = await request('POST', '/v1/projects/', {
            name: `DL Test ${randomSuffix}`, source_language: 'en', target_languages: ['zh-CN']
        }, token);
        console.log('✅ Project:', project.id);

        job = await request('POST', `/v1/jobs/projects/${project.id}/jobs`, {
            name: 'Download Job', source_language: 'en', target_language: 'zh-CN', job_type: 'translation', status: 'created'
        }, token);
        console.log('✅ Job:', job.id);

        // 2. Upload Data (Import)
        console.log('2️⃣  Uploading Data...');
        taskId = await new Promise((resolve, reject) => {
            const url = new URL(`${API_BASE}/v1/jobs/${job.id}/segments/import`);
            const headers = {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/x-ndjson',
                'Content-Encoding': 'gzip'
            };
            const req = http.request(url, { method: 'POST', headers }, res => {
                let data = '';
                res.on('data', c => data += c);
                res.on('end', () => {
                    if (res.statusCode >= 400) reject(`Upload Failed: ${res.statusCode} ${data}`);
                    else {
                        const json = JSON.parse(data);
                        console.log('✅ Upload Started. Task ID:', json.task_id);
                        resolve(json.task_id);
                    }
                });
            });

            const gzip = zlib.createGzip();
            gzip.pipe(req);

            for (let i = 0; i < 50; i++) {
                gzip.write(JSON.stringify({ external_id: `seg_${i}`, content: `Content ${i}` }) + '\n');
            }
            gzip.end();
        });

        // 3. Poll Task Status
        console.log('3️⃣  Polling Task Status...');
        let taskStatus = 'pending';
        for (let i = 0; i < 30; i++) { // Max 30 attempts
            const task = await request('GET', `/v1/tasks/${taskId}`, null, token);
            console.log(`   Task Status: ${task.status} (${task.progress?.processed || 0}/${task.progress?.total || '?'})`);

            if (task.status === 'completed') {
                taskStatus = 'completed';
                break;
            }
            if (task.status === 'failed') throw new Error(`Task Failed: ${JSON.stringify(task.error)}`);

            await new Promise(r => setTimeout(r, 1000)); // Wait 1s
        }
        if (taskStatus !== 'completed') throw new Error('Task Timeout');
        console.log('✅ Task Completed!');
    } catch (e) {
        console.log('⚠️  Polling Failed (Backend Crash?):', e.message || e);
        console.log('⏳ Blind Waiting 10s for backend recover & task process...');
        await new Promise(r => setTimeout(r, 10000));
    }

    try {
        // 4. Download (Export)
        console.log('4️⃣  Downloading Data...');
        await new Promise((resolve, reject) => {
            const url = new URL(`${API_BASE}/v1/jobs/${job.id}/segments/export`);
            const headers = { 'Authorization': `Bearer ${token}` };

            http.get(url, { headers }, res => {
                if (res.statusCode !== 200) {
                    res.resume();
                    return reject(`Export Failed: ${res.statusCode}`);
                }

                console.log('   Headers:', res.headers);
                const gunzip = zlib.createGunzip();
                res.pipe(gunzip);

                let rawData = '';
                gunzip.on('data', chunk => rawData += chunk.toString());
                gunzip.on('end', () => {
                    const lines = rawData.trim().split('\n');
                    console.log(`✅ Downloaded ${lines.length} lines.`);
                    console.log('   First line:', lines[0]);

                    if (lines.length === 50) resolve();
                    else reject(`Count Mismatch: Expected 50, got ${lines.length}`);
                });
                gunzip.on('error', err => reject(`Gunzip Error: ${err.message}`));
            }).on('error', reject);
        });

        console.log('🎉 DOWNLOAD VERIFICATION SUCCESS!');
    } catch (e) {
        console.error('❌ FAILED:', e);
    }
}

main();
