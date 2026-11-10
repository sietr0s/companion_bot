/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ConfigPatch } from '../models/ConfigPatch';
import type { ConfigRead } from '../models/ConfigRead';
import type { ConfigReset } from '../models/ConfigReset';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class ConfigurationService {
    /**
     * Read
     * @returns ConfigRead Successful Response
     * @throws ApiError
     */
    public static readApiV1PublicAuthConfigurationGet(): CancelablePromise<ConfigRead> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/public/auth/configuration',
        });
    }
    /**
     * Patch
     * @param requestBody
     * @returns ConfigRead Successful Response
     * @throws ApiError
     */
    public static patchApiV1PublicAuthConfigurationPatch(
        requestBody: ConfigPatch,
    ): CancelablePromise<ConfigRead> {
        return __request(OpenAPI, {
            method: 'PATCH',
            url: '/api/v1/public/auth/configuration',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Reset
     * @param requestBody
     * @returns ConfigRead Successful Response
     * @throws ApiError
     */
    public static resetApiV1PublicAuthConfigurationResetPost(
        requestBody: ConfigReset,
    ): CancelablePromise<ConfigRead> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/public/auth/configuration/reset',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Read
     * @returns ConfigRead Successful Response
     * @throws ApiError
     */
    public static readApiV1PublicUsersConfigurationGet(): CancelablePromise<ConfigRead> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/public/users/configuration',
        });
    }
    /**
     * Patch
     * @param requestBody
     * @returns ConfigRead Successful Response
     * @throws ApiError
     */
    public static patchApiV1PublicUsersConfigurationPatch(
        requestBody: ConfigPatch,
    ): CancelablePromise<ConfigRead> {
        return __request(OpenAPI, {
            method: 'PATCH',
            url: '/api/v1/public/users/configuration',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Reset
     * @param requestBody
     * @returns ConfigRead Successful Response
     * @throws ApiError
     */
    public static resetApiV1PublicUsersConfigurationResetPost(
        requestBody: ConfigReset,
    ): CancelablePromise<ConfigRead> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/public/users/configuration/reset',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Read
     * @returns ConfigRead Successful Response
     * @throws ApiError
     */
    public static readApiV1PublicLlmConfigurationGet(): CancelablePromise<ConfigRead> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/public/llm/configuration',
        });
    }
    /**
     * Patch
     * @param requestBody
     * @returns ConfigRead Successful Response
     * @throws ApiError
     */
    public static patchApiV1PublicLlmConfigurationPatch(
        requestBody: ConfigPatch,
    ): CancelablePromise<ConfigRead> {
        return __request(OpenAPI, {
            method: 'PATCH',
            url: '/api/v1/public/llm/configuration',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Reset
     * @param requestBody
     * @returns ConfigRead Successful Response
     * @throws ApiError
     */
    public static resetApiV1PublicLlmConfigurationResetPost(
        requestBody: ConfigReset,
    ): CancelablePromise<ConfigRead> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/public/llm/configuration/reset',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Read
     * @returns ConfigRead Successful Response
     * @throws ApiError
     */
    public static readApiV1PublicTelegramConfigurationGet(): CancelablePromise<ConfigRead> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/public/telegram/configuration',
        });
    }
    /**
     * Patch
     * @param requestBody
     * @returns ConfigRead Successful Response
     * @throws ApiError
     */
    public static patchApiV1PublicTelegramConfigurationPatch(
        requestBody: ConfigPatch,
    ): CancelablePromise<ConfigRead> {
        return __request(OpenAPI, {
            method: 'PATCH',
            url: '/api/v1/public/telegram/configuration',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Reset
     * @param requestBody
     * @returns ConfigRead Successful Response
     * @throws ApiError
     */
    public static resetApiV1PublicTelegramConfigurationResetPost(
        requestBody: ConfigReset,
    ): CancelablePromise<ConfigRead> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/public/telegram/configuration/reset',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Read
     * @returns ConfigRead Successful Response
     * @throws ApiError
     */
    public static readApiV1PublicInstagramConfigurationGet(): CancelablePromise<ConfigRead> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/public/instagram/configuration',
        });
    }
    /**
     * Patch
     * @param requestBody
     * @returns ConfigRead Successful Response
     * @throws ApiError
     */
    public static patchApiV1PublicInstagramConfigurationPatch(
        requestBody: ConfigPatch,
    ): CancelablePromise<ConfigRead> {
        return __request(OpenAPI, {
            method: 'PATCH',
            url: '/api/v1/public/instagram/configuration',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Reset
     * @param requestBody
     * @returns ConfigRead Successful Response
     * @throws ApiError
     */
    public static resetApiV1PublicInstagramConfigurationResetPost(
        requestBody: ConfigReset,
    ): CancelablePromise<ConfigRead> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/public/instagram/configuration/reset',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Read
     * @returns ConfigRead Successful Response
     * @throws ApiError
     */
    public static readApiV1PublicSttConfigurationGet(): CancelablePromise<ConfigRead> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/public/stt/configuration',
        });
    }
    /**
     * Patch
     * @param requestBody
     * @returns ConfigRead Successful Response
     * @throws ApiError
     */
    public static patchApiV1PublicSttConfigurationPatch(
        requestBody: ConfigPatch,
    ): CancelablePromise<ConfigRead> {
        return __request(OpenAPI, {
            method: 'PATCH',
            url: '/api/v1/public/stt/configuration',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Reset
     * @param requestBody
     * @returns ConfigRead Successful Response
     * @throws ApiError
     */
    public static resetApiV1PublicSttConfigurationResetPost(
        requestBody: ConfigReset,
    ): CancelablePromise<ConfigRead> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/public/stt/configuration/reset',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Read
     * @returns ConfigRead Successful Response
     * @throws ApiError
     */
    public static readApiV1PublicTtsConfigurationGet(): CancelablePromise<ConfigRead> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/public/tts/configuration',
        });
    }
    /**
     * Patch
     * @param requestBody
     * @returns ConfigRead Successful Response
     * @throws ApiError
     */
    public static patchApiV1PublicTtsConfigurationPatch(
        requestBody: ConfigPatch,
    ): CancelablePromise<ConfigRead> {
        return __request(OpenAPI, {
            method: 'PATCH',
            url: '/api/v1/public/tts/configuration',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Reset
     * @param requestBody
     * @returns ConfigRead Successful Response
     * @throws ApiError
     */
    public static resetApiV1PublicTtsConfigurationResetPost(
        requestBody: ConfigReset,
    ): CancelablePromise<ConfigRead> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/public/tts/configuration/reset',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Read
     * @returns ConfigRead Successful Response
     * @throws ApiError
     */
    public static readApiV1PublicMemoryConfigurationGet(): CancelablePromise<ConfigRead> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/public/memory/configuration',
        });
    }
    /**
     * Patch
     * @param requestBody
     * @returns ConfigRead Successful Response
     * @throws ApiError
     */
    public static patchApiV1PublicMemoryConfigurationPatch(
        requestBody: ConfigPatch,
    ): CancelablePromise<ConfigRead> {
        return __request(OpenAPI, {
            method: 'PATCH',
            url: '/api/v1/public/memory/configuration',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Reset
     * @param requestBody
     * @returns ConfigRead Successful Response
     * @throws ApiError
     */
    public static resetApiV1PublicMemoryConfigurationResetPost(
        requestBody: ConfigReset,
    ): CancelablePromise<ConfigRead> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/public/memory/configuration/reset',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Read
     * @returns ConfigRead Successful Response
     * @throws ApiError
     */
    public static readApiV1PublicBehaviorConfigurationGet(): CancelablePromise<ConfigRead> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/public/behavior/configuration',
        });
    }
    /**
     * Patch
     * @param requestBody
     * @returns ConfigRead Successful Response
     * @throws ApiError
     */
    public static patchApiV1PublicBehaviorConfigurationPatch(
        requestBody: ConfigPatch,
    ): CancelablePromise<ConfigRead> {
        return __request(OpenAPI, {
            method: 'PATCH',
            url: '/api/v1/public/behavior/configuration',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Reset
     * @param requestBody
     * @returns ConfigRead Successful Response
     * @throws ApiError
     */
    public static resetApiV1PublicBehaviorConfigurationResetPost(
        requestBody: ConfigReset,
    ): CancelablePromise<ConfigRead> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/public/behavior/configuration/reset',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Read
     * @returns ConfigRead Successful Response
     * @throws ApiError
     */
    public static readApiV1PublicBatchingConfigurationGet(): CancelablePromise<ConfigRead> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/public/batching/configuration',
        });
    }
    /**
     * Patch
     * @param requestBody
     * @returns ConfigRead Successful Response
     * @throws ApiError
     */
    public static patchApiV1PublicBatchingConfigurationPatch(
        requestBody: ConfigPatch,
    ): CancelablePromise<ConfigRead> {
        return __request(OpenAPI, {
            method: 'PATCH',
            url: '/api/v1/public/batching/configuration',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Reset
     * @param requestBody
     * @returns ConfigRead Successful Response
     * @throws ApiError
     */
    public static resetApiV1PublicBatchingConfigurationResetPost(
        requestBody: ConfigReset,
    ): CancelablePromise<ConfigRead> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/public/batching/configuration/reset',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Read
     * @returns ConfigRead Successful Response
     * @throws ApiError
     */
    public static readApiV1PublicOrchestratorConfigurationGet(): CancelablePromise<ConfigRead> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/public/orchestrator/configuration',
        });
    }
    /**
     * Patch
     * @param requestBody
     * @returns ConfigRead Successful Response
     * @throws ApiError
     */
    public static patchApiV1PublicOrchestratorConfigurationPatch(
        requestBody: ConfigPatch,
    ): CancelablePromise<ConfigRead> {
        return __request(OpenAPI, {
            method: 'PATCH',
            url: '/api/v1/public/orchestrator/configuration',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Reset
     * @param requestBody
     * @returns ConfigRead Successful Response
     * @throws ApiError
     */
    public static resetApiV1PublicOrchestratorConfigurationResetPost(
        requestBody: ConfigReset,
    ): CancelablePromise<ConfigRead> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/public/orchestrator/configuration/reset',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
