import { AuthService } from '../../shared/api-client/src/generated/services/AuthService';
import { OpenAPI } from '../../shared/api-client/src/generated/core/OpenAPI';

declare const process: any;

OpenAPI.BASE = 'http://127.0.0.1:8000';

const randomSuffix = Math.floor(Math.random() * 10000);
const TEST_USER = {
    username: `devbot${randomSuffix}`,
    email: `dev_bot_${randomSuffix}@example.com`,
    password: 'Str0ngP@ssw0rd!2025'
};

async function main() {
    // 1. Try Register
    console.log(`Trying to register ${TEST_USER.username} (${TEST_USER.email})...`);
    try {
        const regRes = await AuthService.registerV1AuthRegisterPost({
            username: TEST_USER.username,
            email: TEST_USER.email,
            password: TEST_USER.password,
            display_name: 'Dev Bot'
        });
        console.log('✅ Registration Successful:', JSON.stringify(regRes));
    } catch (error: any) {
        console.error('⚠️ Registration Failed:', error.status);
        if (error.body) console.error('Error Body:', JSON.stringify(error.body, null, 2));
    }

    // 2. Login
    console.log('Testing Login...');
    try {
        const response = await AuthService.loginPasswordV1AuthLoginPasswordPost({
            username_or_email: TEST_USER.email,
            password: TEST_USER.password
        });
        console.log('✅ Login Successful!');
        console.log('Access Token:', response.access_token.slice(0, 20) + '...');
        console.log('User ID:', response.user.id);
    } catch (error: any) {
        console.error('❌ Login Failed');
        console.error('Status:', error.status);
        console.error('Body:', JSON.stringify(error.body, null, 2));
        process.exit(1);
    }
}

main();
