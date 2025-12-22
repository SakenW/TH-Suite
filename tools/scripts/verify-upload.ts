
import { AuthService } from '../../shared/api-client/src/generated/services/AuthService';
import { ProjectsService } from '../../shared/api-client/src/generated/services/ProjectsService';
import { JobsService } from '../../shared/api-client/src/generated/services/JobsService';
import { OpenAPI } from '../../shared/api-client/src/generated/core/OpenAPI';
import { TransHubClient } from '../../shared/api-client/src/client';
// EXPLICITLY IMPORT NODE IMPLEMENTATION FOR THIS SCRIPT
import { createGzipNdjsonBody } from '../../shared/api-client/src/streaming.node';

declare const process: any;

// 1. Setup
OpenAPI.BASE = 'http://127.0.0.1:8000';
const randomSuffix = Math.floor(Math.random() * 10000);
const USER = {
    username: `devbot${randomSuffix}`,
    email: `uploader_${randomSuffix}@example.com`,
    password: 'Str0ngP@ssw0rd!2025'
};

async function main() {
    try {
        // 2. Auth
        console.log('[1/4] Registering User...');
        await AuthService.registerV1AuthRegisterPost({
            username: USER.username,
            email: USER.email,
            password: USER.password,
            display_name: 'Uploader Bot'
        });

        console.log('[2/4] Logging in...');
        const authRes = await AuthService.loginPasswordV1AuthLoginPasswordPost({
            username_or_email: USER.email,
            password: USER.password
        });
        const token = authRes.access_token;
        OpenAPI.TOKEN = token; // Set global token for generated services

        // 3. Create Project
        console.log('[3/4] Creating Project...');
        const project = await ProjectsService.createProjectV1ProjectsPost({
            name: `Test Project ${randomSuffix}`,
            source_language: 'en',
            target_languages: ['zh-CN', 'ja']
        });
        console.log(`✅ Project Created: ${project.id}`);

        // 4. Create Job
        console.log('[3.5/4] Creating Job...');
        const job = await JobsService.createJobV1JobsProjectsProjectIdJobsPost(
            project.id,
            {
                name: 'Test Upload Job',
                source_language: 'en',
                target_language: 'zh-CN',
                job_type: 'translation'
            }
        );
        // @ts-ignore
        const jobId = job.id; // Generated type might return Record<string, any>
        console.log(`✅ Job Created: ${jobId}`);


        // 5. Upload Segments (using Manual Request with Node Stream)
        console.log('[4/4] Uploading Segments via Stream...');

        // Manual fetch because Client defaults to Browser implementation
        const segments = [];
        for (let i = 0; i < 100; i++) {
            segments.push({
                external_id: `seg_${i}`,
                content: `This is segment number ${i} for testing upload.`,
                context: `Context ${i}`
            });
        }

        const bodyStream = await createGzipNdjsonBody(segments);

        // Use native fetch (Node 18+)
        const response = await fetch(`${OpenAPI.BASE}/v1/jobs/${jobId}/segments/import`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/x-ndjson',
                'Content-Encoding': 'gzip'
            },
            body: bodyStream as any,
            // @ts-ignore
            duplex: 'half'
        });

        if (!response.ok) {
            const txt = await response.text();
            throw new Error(`Upload Failed: ${response.status} ${txt}`);
        }

        const uploadRes = await response.json();
        console.log('✅ Upload Response:', JSON.stringify(uploadRes));

    } catch (error: any) {
        console.error('❌ Failed:', error.status || error.message);
        if (error.body) console.error(JSON.stringify(error.body, null, 2));
        process.exit(1);
    }
}

main();
