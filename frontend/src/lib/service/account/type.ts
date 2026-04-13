export interface User {
    id: string;
    email: string;
    name: string;
    provider: string;
    createAt: string;
    role: string;
    permissions: string[];
    active: boolean;
}

export interface LoginRequest {
    username: string;
    password: string;
}

export interface LoginResponse {
    access_token: string;
}

export interface UserProfile {
    id: string;
    role: string;
    username: string;
}
