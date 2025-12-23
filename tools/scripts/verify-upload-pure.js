
const http = require('http');
const zlib = require('zlib');

async function main() {
    console.log('Starting Pure Node.js Upload Test...');

    const API_BASE = 'http://127.0.0.1:8000';
    const randomSuffix = Math.floor(Math.random() * 10000);
    const USER = {
        username: `devbot${randomSuffix}`,
        email: `uploader_${randomSuffix}@example.com`,
        password: 'Str0ngP@ssw0rd!2025'
    };

    // Helper for simple JSON POST
    async function post(path, body, token = null) {
        return new Promise((resolve, reject) => {
            const url = new URL(API_BASE + path);
            const headers = { 'Content-Type': 'application/json' };
            if (token) headers['Authorization'] = `Bearer ${token}`;

            const req = http.request(url, { method: 'POST', headers }, res => {
                let data = '';
                res.on('data', chunk => data += chunk);
                res.on('end', () => {
                    try {
                        const json = JSON.parse(data);
                        if (res.statusCode >= 400) reject({ status: res.statusCode, body: json });
                        else resolve(json);
                    } catch (e) {
                        resolve(data); // text response?
                    }
                });
            });
            req.on('error', reject);
            req.write(JSON.stringify(body));
            req.end();
        });
    }

    try {
        // 1. Register & Login
        try {
            await post('/v1/auth/register', { ...USER, display_name: 'Uploader' });
            console.log('✅ Registered');
        } catch (e) { console.log('⚠️  Register failed (maybe exists)'); }

        const loginRes = await post('/v1/auth/login/password', { username_or_email: USER.email, password: USER.password });
        const token = loginRes.access_token;
        console.log('✅ Logged in');

        // 2. Project & Job
        const project = await post('/v1/projects/', {
            name: `Test Pj ${randomSuffix}`, source_language: 'en', target_languages: ['zh-CN']
        }, token);
        console.log('✅ Project:', project.id);

        const job = await post(`/v1/jobs/projects/${project.id}/jobs`, {
            name: 'Upload Job', source_language: 'en', target_language: 'zh-CN', job_type: 'translation', status: 'created'
        }, token);
        console.log('✅ Job Response:', JSON.stringify(job, null, 2));
        console.log('✅ Job:', job.id);

        // 3. Streaming Upload
        console.log('📤 Starting Stream Upload...');

        await new Promise((resolve, reject) => {
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
                    console.log('✅ Upload Status:', res.statusCode);
                    console.log('✅ Response:', data);
                    resolve();
                });
            });

            req.on('error', reject);

            const gzip = zlib.createGzip();
            gzip.pipe(req);

            // Stream data
            let i = 0;
            function push() {
                if (i >= 50) {
                    gzip.end();
                    return;
                }
                const seg = { external_id: `s_${i}`, content: `Segment ${i}` };
                const ok = gzip.write(JSON.stringify(seg) + '\n');
                i++;
                if (ok) setImmediate(push);
                else gzip.once('drain', push);
            }
            push();
        });

    } catch (e) {
        console.error('❌ Error:', e);
    }
}

main();
