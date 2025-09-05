Access to fetch at 'http://localhost:18000/scan-results/9c7ae6df-f2cf-44d4-9e2c-69f2caa2e4e5' from origin 'http://127.0.0.1:5173' has been blocked by CORS policy: No 'Access-Control-Allow-Origin' header is present on the requested resource.了解此错误
baseApiService.ts:70  GET http://localhost:18000/scan-results/9c7ae6df-f2cf-44d4-9e2c-69f2caa2e4e5 net::ERR_FAILED 500 (Internal Server Error)
request @ baseApiService.ts:70
get @ baseApiService.ts:204
getResults @ scanService.ts:122
（匿名） @ useRealTimeProgress.ts:182
await in （匿名）
poll @ useRealTimeProgress.ts:268
setTimeout
poll @ useRealTimeProgress.ts:273
setTimeout
poll @ useRealTimeProgress.ts:273
setTimeout
poll @ useRealTimeProgress.ts:273
setTimeout
poll @ useRealTimeProgress.ts:273
setTimeout
poll @ useRealTimeProgress.ts:273
setTimeout
poll @ useRealTimeProgress.ts:273了解此错误
baseApiService.ts:144 API request failed: TypeError: Failed to fetch
    at BaseApiService.request (baseApiService.ts:70:28)
    at BaseApiService.get (baseApiService.ts:204:17)
    at ScanService.getResults (scanService.ts:122:45)
    at useRealTimeProgress.ts:182:54
handleError @ baseApiService.ts:144
request @ baseApiService.ts:92
await in request
get @ baseApiService.ts:204
getResults @ scanService.ts:122
（匿名） @ useRealTimeProgress.ts:182
await in （匿名）
poll @ useRealTimeProgress.ts:268
setTimeout
poll @ useRealTimeProgress.ts:273
setTimeout
poll @ useRealTimeProgress.ts:273
setTimeout
poll @ useRealTimeProgress.ts:273
setTimeout
poll @ useRealTimeProgress.ts:273
setTimeout
poll @ useRealTimeProgress.ts:273
setTimeout
poll @ useRealTimeProgress.ts:273了解此错误
useRealTimeProgress.ts:264 ⏹️ 轮询已停止，不再安排下次轮询