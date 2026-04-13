import axios, { AxiosInstance } from 'axios';
import { getApiUrl } from './api-url';
import { useAuthStore } from '../stores/auth-store';

const apiUrl = getApiUrl();

export interface Pagination<T> {
    totalElements: number;
    content: T[];
}

export interface ApiResponse<T = unknown> {
    code: number;
    message: string;
    result?: T;
}

export class ApiError extends Error {
    status?: number;
    details: Record<string, string>;

    constructor(
        message: string,
        options?: {
            status?: number;
            details?: Record<string, string>;
        },
    ) {
        super(message);
        this.name = 'ApiError';
        this.status = options?.status;
        this.details = options?.details ?? {};
    }
}

export const axiosWrapper: AxiosInstance = axios.create({
    baseURL: apiUrl,
    withCredentials: true,
    validateStatus: () => true,
    headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
    },
});

axiosWrapper.interceptors.request.use(
    (config) => {
        const token = useAuthStore.getState().accessToken;
        console.log('Here is the token', token);

        if (token) {
            config.headers['Authorization'] = `Bearer ${token}`;
        }

        return config;
    },
    (error) => {
        return Promise.reject(error);
    },
);

export const throwIfError = (data: ApiResponse, status?: number) => {
    if (status && status >= 400) {
        if (data?.message) {
            throw new ApiError(data.message, { status });
        }
        throw new ApiError('Unexpected server error', { status });
    }
    if (data && data.code !== 1000) {
        throw new ApiError(data.message ?? 'Unknown error', { status });
    }
};

export const deserialize = <T>(data: ApiResponse): T => {
    return data.result as T;
};
