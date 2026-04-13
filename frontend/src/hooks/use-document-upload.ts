'use client';

import { useMutation } from '@tanstack/react-query';
import { documentService } from '@/lib/service/document';

interface UseDocumentUploadOptions {
    onStatusChange?: (fileId: string, status: 'uploading' | 'processing' | 'ready' | 'failed') => void;
    onError?: (fileId: string, error: Error) => void;
}

/**
 * Custom hook for uploading documents via the S3 presigned URL pipeline.
 *
 * Flow: uploading → processing → ready (or failed on any error)
 */
export function useDocumentUpload(options?: UseDocumentUploadOptions) {
    const mutation = useMutation({
        mutationFn: async ({ file, fileId }: { file: File; fileId: string }) => {
            // Status: uploading (already set by the caller before invoking)

            // Step 1 + 2: get presigned URL and upload to S3
            const { presignedUrl, fileKey } = await documentService.getPresignedUrl(file.name);
            await documentService.uploadToS3(presignedUrl, file);

            // Status: processing — S3 upload done, confirming with backend
            options?.onStatusChange?.(fileId, 'processing');

            // Step 3: confirm upload → triggers AI pipeline
            await documentService.confirmUpload(fileKey);

            // Status: ready — backend acknowledged
            options?.onStatusChange?.(fileId, 'ready');

            return { fileKey, fileId };
        },
        onError: (error: Error, variables) => {
            options?.onStatusChange?.(variables.fileId, 'failed');
            options?.onError?.(variables.fileId, error);
        },
    });

    const uploadFile = (file: File, fileId: string) => {
        mutation.mutate({ file, fileId });
    };

    return {
        uploadFile,
        isUploading: mutation.isPending,
    };
}
