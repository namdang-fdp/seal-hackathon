import { LoginRequest, LoginResponse, UserProfile } from "./type";
import { axiosWrapper, deserialize, ApiResponse } from '../../api/axios-config';

export const authService = {
    login: async (payload: LoginRequest): Promise<LoginResponse> => {
        const { data } = await axiosWrapper.post<ApiResponse<LoginResponse>>('/auth/login', payload);
        return deserialize<LoginResponse>(data);
    },
    
    getMe: async (): Promise<UserProfile> => {
        const { data } = await axiosWrapper.get<ApiResponse<UserProfile>>('/auth/me');
        return deserialize<UserProfile>(data);
    }
};
