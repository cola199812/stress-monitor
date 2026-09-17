import axios from 'axios';

const http = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_BASE_URL || 'http://127.0.0.1:5050',
  timeout: 10000,
  withCredentials: true, // 支持跨域凭证
});


// 简单的延迟函数
function delay(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

// 计算退避间隔
function getBackoffDelay(base: number, attempt: number, jitter = true) {
  const exp = base * Math.pow(2, attempt);
  if (!jitter) return exp;
  const rand = Math.random() * base;
  return exp + rand; // 抖动，避免惊群
}

http.interceptors.request.use(
  (config) => {
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

http.interceptors.response.use(
  (response) => {
    return response.data;
  },
  async (error) => {
    const config: any = error?.config || {};
    const method = String(config.method || 'get').toLowerCase();
    const status = error?.response?.status;
    const code = error?.code;

    // 允许每个请求自定义重试次数与基准延迟；默认 GET 重试 2 次
    const maxRetries = (config.retry?.attempts ?? (method === 'get' ? 2 : 0)) as number;
    const baseDelay = (config.retry?.delayMs ?? 700) as number; // 基础 700ms

    config.__retryCount = config.__retryCount || 0;
    const isTimeout = code === 'ECONNABORTED' || /timeout/i.test(error?.message || '');
    const isNetwork = !error?.response;
    const isRetriableStatus = status === 429 || status === 500 || status === 502 || status === 503 || status === 504;
    const shouldRetry = config.__retryCount < maxRetries && (isTimeout || isNetwork || isRetriableStatus);

    if (shouldRetry) {
      const wait = getBackoffDelay(baseDelay, config.__retryCount);
      config.__retryCount += 1;
      await delay(wait);
      return http(config);
    }

    // 最终失败：GET 请求静默降级为空数据，避免 UI 报错
    if (method === 'get') {
      const fallback = config.fallbackData ?? { items: [], page: 1, pageSize: 0, total: 0 };
      return Promise.resolve(fallback);
    }

    return Promise.reject(error);
  }
);

export default http;