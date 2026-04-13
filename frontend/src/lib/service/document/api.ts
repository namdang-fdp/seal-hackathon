import { PresignedUrlResponse, ConfirmUploadResponse } from './type';
import { axiosWrapper, deserialize, ApiResponse } from '../../api/axios-config';

export const documentService = {
    /**
     * Step 1: Get a presigned URL from the backend for uploading to S3.
     */
    getPresignedUrl: async (fileName: string): Promise<PresignedUrlResponse> => {
        const { data } = await axiosWrapper.get<ApiResponse<PresignedUrlResponse>>(
            '/documents/presigned-url',
            { params: { fileName } },
        );
        return deserialize<PresignedUrlResponse>(data);
    },

    /**
     * Step 2: Upload file directly to S3 using the presigned URL.
     * Uses raw fetch — no Authorization header (the URL itself contains the signature).
     */
    uploadToS3: async (presignedUrl: string, file: File): Promise<void> => {
        const res = await fetch(presignedUrl, {
            method: 'PUT',
            body: file,
            headers: {
                'Content-Type': file.type || 'application/octet-stream',
            },
        });
        if (!res.ok) {
            throw new Error(`S3 upload failed with status ${res.status}`);
        }
    },

    /**
     * Step 3: Confirm the upload so the backend triggers the AI pipeline.
     */
    confirmUpload: async (fileKey: string): Promise<ConfirmUploadResponse> => {
        const { data } = await axiosWrapper.post<ApiResponse<ConfirmUploadResponse>>(
            '/documents/confirm',
            { fileKey },
        );
        return deserialize<ConfirmUploadResponse>(data);
    },

    /**
     * Orchestrates the full 3-step upload flow.
     * Returns the fileKey for tracking.
     */
    uploadDocument: async (file: File): Promise<{ fileKey: string }> => {
        // Step 1
        const { presignedUrl, fileKey } = await documentService.getPresignedUrl(file.name);

        // Step 2
        await documentService.uploadToS3(presignedUrl, file);

        // Step 3
        await documentService.confirmUpload(fileKey);

        return { fileKey };
    },
};
