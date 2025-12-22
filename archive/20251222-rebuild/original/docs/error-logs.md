核心错误摘要
主要问题：后端服务完全无法连接，导致网络超时。
之前的错误是服务器还能响应，但报告了内部错误（500）。现在的错误是，前端应用（浏览器）在规定时间内根本无法从后端服务器 http://localhost:18000 收到任何响应，直接导致了连接超时。
关键信息点
网络连接超时 (最关键的错误):
错误信息: net::ERR_CONNECTION_TIMED_OUT
说明: 这不是一个HTTP状态码（如500），而是一个更底层的网络错误。它意味着你的前端应用向后端地址发送了请求，但后端服务没有在预设的时间内应答。
受影响的API:
GET http://localhost:18000/api/v1/scan/test
GET http://localhost:18000/api/v1/scan/active
应用内部日志确认了问题:
你的代码在 BaseApiClient.ts 中正确地捕获并报告了这些网络问题。
❌ API Error: NETWORK /api/v1/scan/test
❌ API Error: NETWORK /api/v1/scan/active
在应用启动时，就已经检测到了连接超时。
⏰ Backend connection timeout, but continuing...
次要问题 (可能与主要问题相关):
在日志中，仍然出现了 POST http://localhost:18000/api/v1/scan/start 500 (Internal Server Error)。
这说明后端服务非常不稳定：有时完全不响应（超时），有时能响应但内部又出错了。
可以忽略的干扰信息:
Not running in Tauri environment: 这只是一个环境检测信息，说明你的应用正以普通网页模式运行，是正常的。
React Router Future Flag Warning: 这是 react-router-dom 库的升级提示，与网络问题无关。
