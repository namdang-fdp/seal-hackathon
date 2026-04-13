export interface PresignedUrlResponse {
    presignedUrl: string;
    fileKey: string;
}

export interface ConfirmUploadRequest {
    fileKey: string;
}

export interface ConfirmUploadResponse {
    status: string;
    message: string;
    fileKey: string;
}
