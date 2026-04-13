package com.ragnarok.seal.controller;

import com.ragnarok.seal.dto.ConfirmUploadRequest;
import com.ragnarok.seal.dto.PresignedUrlResponse;
import com.ragnarok.seal.service.AiOrchestratorService;
import com.ragnarok.seal.service.S3Service;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@Slf4j
@RestController
@RequestMapping("/api/v1/documents")
@RequiredArgsConstructor
public class DocumentController {

    private final S3Service s3Service;
    private final AiOrchestratorService aiOrchestratorService;

    /**
     * Frontend gọi để lấy presigned URL upload file lên S3.
     */
    @GetMapping("/presigned-url")
    public ResponseEntity<PresignedUrlResponse> getPresignedUrl(@RequestParam String fileName) {
        log.info("Request presigned URL for fileName: {}", fileName);

        PresignedUrlResponse response = s3Service.generatePresignedUrl(fileName);

        return ResponseEntity.ok(response);
    }

    /**
     * Frontend gọi sau khi upload xong lên S3.
     * Backend trigger AI pipeline rồi trả 200 OK ngay lập tức.
     */
    @PostMapping("/confirm")
    public ResponseEntity<Map<String, String>> confirmUpload(@RequestBody ConfirmUploadRequest request) {
        log.info("Upload confirmed for fileKey: {}", request.fileKey());

        aiOrchestratorService.triggerAiPipeline(request.fileKey());

        return ResponseEntity.ok(Map.of(
                "status", "processing",
                "message", "File đã nhận, đang xử lý AI pipeline.",
                "fileKey", request.fileKey()));
    }
}
