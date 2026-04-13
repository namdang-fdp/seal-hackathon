package com.ragnarok.seal.service;

import com.ragnarok.seal.dto.AiProcessRequest;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.web.reactive.function.client.WebClient;

@Slf4j
@Service
@RequiredArgsConstructor
public class AiOrchestratorService {

    private final WebClient aiServiceWebClient;

    /**
     * Gọi POST sang Python AI Service để trigger luồng chunking.
     * Subscribe bất đồng bộ — không block thread của controller.
     *
     * @param fileKey S3 key của file đã upload
     */
    public void triggerAiPipeline(String fileKey) {
        log.info("Triggering AI pipeline for fileKey: {}", fileKey);

        aiServiceWebClient.post()
                .uri("/api/process")
                .bodyValue(new AiProcessRequest(fileKey))
                .retrieve()
                .bodyToMono(String.class)
                .subscribe(
                        response -> log.info("AI Service responded for fileKey {}: {}", fileKey, response),
                        error -> log.error("AI Service call failed for fileKey {}: {}", fileKey, error.getMessage()));
    }
}
