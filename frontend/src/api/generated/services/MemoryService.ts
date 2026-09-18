/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ConversationCreate } from '../models/ConversationCreate';
import type { ConversationRead } from '../models/ConversationRead';
import type { ConversationUpdate } from '../models/ConversationUpdate';
import type { MemoryMessageCreate } from '../models/MemoryMessageCreate';
import type { MemoryMessageRead } from '../models/MemoryMessageRead';
import type { MemoryMessageUpdate } from '../models/MemoryMessageUpdate';
import type { PaginatedResponse_ConversationRead_ } from '../models/PaginatedResponse_ConversationRead_';
import type { PaginatedResponse_MemoryMessageRead_ } from '../models/PaginatedResponse_MemoryMessageRead_';
import type { PaginatedResponse_SummaryStateRead_ } from '../models/PaginatedResponse_SummaryStateRead_';
import type { PaginatedResponse_VectorRecordRead_ } from '../models/PaginatedResponse_VectorRecordRead_';
import type { SummaryStateCreate } from '../models/SummaryStateCreate';
import type { SummaryStateRead } from '../models/SummaryStateRead';
import type { SummaryStateUpdate } from '../models/SummaryStateUpdate';
import type { VectorRecordCreate } from '../models/VectorRecordCreate';
import type { VectorRecordRead } from '../models/VectorRecordRead';
import type { VectorRecordUpdate } from '../models/VectorRecordUpdate';
import type { VectorTopicDetailRead } from '../models/VectorTopicDetailRead';
import type { VectorTopicRead } from '../models/VectorTopicRead';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class MemoryService {
    /**
     * Get List
     * @param page
     * @param pageSize
     * @param orderBy
     * @returns PaginatedResponse_ConversationRead_ Successful Response
     * @throws ApiError
     */
    public static getListApiV1PublicMemoryConversationsGet(
        page: number = 1,
        pageSize: number = 100,
        orderBy?: (string | null),
    ): CancelablePromise<PaginatedResponse_ConversationRead_> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/public/memory/conversations/',
            query: {
                'page': page,
                'page_size': pageSize,
                'order_by': orderBy,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Create
     * @param requestBody
     * @returns ConversationRead Successful Response
     * @throws ApiError
     */
    public static createApiV1PublicMemoryConversationsPost(
        requestBody: ConversationCreate,
    ): CancelablePromise<ConversationRead> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/public/memory/conversations/',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get By Id
     * @param itemId
     * @returns ConversationRead Successful Response
     * @throws ApiError
     */
    public static getByIdApiV1PublicMemoryConversationsItemIdGet(
        itemId: string,
    ): CancelablePromise<ConversationRead> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/public/memory/conversations/{item_id}',
            path: {
                'item_id': itemId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Update
     * @param itemId
     * @param requestBody
     * @returns ConversationRead Successful Response
     * @throws ApiError
     */
    public static updateApiV1PublicMemoryConversationsItemIdPut(
        itemId: string,
        requestBody: ConversationUpdate,
    ): CancelablePromise<ConversationRead> {
        return __request(OpenAPI, {
            method: 'PUT',
            url: '/api/v1/public/memory/conversations/{item_id}',
            path: {
                'item_id': itemId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Delete
     * @param itemId
     * @returns void
     * @throws ApiError
     */
    public static deleteApiV1PublicMemoryConversationsItemIdDelete(
        itemId: string,
    ): CancelablePromise<void> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/api/v1/public/memory/conversations/{item_id}',
            path: {
                'item_id': itemId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get List
     * @param page
     * @param pageSize
     * @param orderBy
     * @returns PaginatedResponse_MemoryMessageRead_ Successful Response
     * @throws ApiError
     */
    public static getListApiV1PublicMemoryMessagesGet(
        page: number = 1,
        pageSize: number = 100,
        orderBy?: (string | null),
    ): CancelablePromise<PaginatedResponse_MemoryMessageRead_> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/public/memory/messages/',
            query: {
                'page': page,
                'page_size': pageSize,
                'order_by': orderBy,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Create
     * @param requestBody
     * @returns MemoryMessageRead Successful Response
     * @throws ApiError
     */
    public static createApiV1PublicMemoryMessagesPost(
        requestBody: MemoryMessageCreate,
    ): CancelablePromise<MemoryMessageRead> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/public/memory/messages/',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get By Id
     * @param itemId
     * @returns MemoryMessageRead Successful Response
     * @throws ApiError
     */
    public static getByIdApiV1PublicMemoryMessagesItemIdGet(
        itemId: string,
    ): CancelablePromise<MemoryMessageRead> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/public/memory/messages/{item_id}',
            path: {
                'item_id': itemId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Update
     * @param itemId
     * @param requestBody
     * @returns MemoryMessageRead Successful Response
     * @throws ApiError
     */
    public static updateApiV1PublicMemoryMessagesItemIdPut(
        itemId: string,
        requestBody: MemoryMessageUpdate,
    ): CancelablePromise<MemoryMessageRead> {
        return __request(OpenAPI, {
            method: 'PUT',
            url: '/api/v1/public/memory/messages/{item_id}',
            path: {
                'item_id': itemId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Delete
     * @param itemId
     * @returns void
     * @throws ApiError
     */
    public static deleteApiV1PublicMemoryMessagesItemIdDelete(
        itemId: string,
    ): CancelablePromise<void> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/api/v1/public/memory/messages/{item_id}',
            path: {
                'item_id': itemId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get List
     * @param page
     * @param pageSize
     * @param orderBy
     * @returns PaginatedResponse_SummaryStateRead_ Successful Response
     * @throws ApiError
     */
    public static getListApiV1PublicMemorySummaryStatesGet(
        page: number = 1,
        pageSize: number = 100,
        orderBy?: (string | null),
    ): CancelablePromise<PaginatedResponse_SummaryStateRead_> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/public/memory/summary-states/',
            query: {
                'page': page,
                'page_size': pageSize,
                'order_by': orderBy,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Create
     * @param requestBody
     * @returns SummaryStateRead Successful Response
     * @throws ApiError
     */
    public static createApiV1PublicMemorySummaryStatesPost(
        requestBody: SummaryStateCreate,
    ): CancelablePromise<SummaryStateRead> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/public/memory/summary-states/',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get By Id
     * @param itemId
     * @returns SummaryStateRead Successful Response
     * @throws ApiError
     */
    public static getByIdApiV1PublicMemorySummaryStatesItemIdGet(
        itemId: string,
    ): CancelablePromise<SummaryStateRead> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/public/memory/summary-states/{item_id}',
            path: {
                'item_id': itemId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Update
     * @param itemId
     * @param requestBody
     * @returns SummaryStateRead Successful Response
     * @throws ApiError
     */
    public static updateApiV1PublicMemorySummaryStatesItemIdPut(
        itemId: string,
        requestBody: SummaryStateUpdate,
    ): CancelablePromise<SummaryStateRead> {
        return __request(OpenAPI, {
            method: 'PUT',
            url: '/api/v1/public/memory/summary-states/{item_id}',
            path: {
                'item_id': itemId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Delete
     * @param itemId
     * @returns void
     * @throws ApiError
     */
    public static deleteApiV1PublicMemorySummaryStatesItemIdDelete(
        itemId: string,
    ): CancelablePromise<void> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/api/v1/public/memory/summary-states/{item_id}',
            path: {
                'item_id': itemId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get List
     * @param page
     * @param pageSize
     * @param orderBy
     * @returns PaginatedResponse_VectorRecordRead_ Successful Response
     * @throws ApiError
     */
    public static getListApiV1PublicMemoryVectorRecordsGet(
        page: number = 1,
        pageSize: number = 100,
        orderBy?: (string | null),
    ): CancelablePromise<PaginatedResponse_VectorRecordRead_> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/public/memory/vector-records/',
            query: {
                'page': page,
                'page_size': pageSize,
                'order_by': orderBy,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Create
     * @param requestBody
     * @returns VectorRecordRead Successful Response
     * @throws ApiError
     */
    public static createApiV1PublicMemoryVectorRecordsPost(
        requestBody: VectorRecordCreate,
    ): CancelablePromise<VectorRecordRead> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/public/memory/vector-records/',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get By Id
     * @param itemId
     * @returns VectorRecordRead Successful Response
     * @throws ApiError
     */
    public static getByIdApiV1PublicMemoryVectorRecordsItemIdGet(
        itemId: string,
    ): CancelablePromise<VectorRecordRead> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/public/memory/vector-records/{item_id}',
            path: {
                'item_id': itemId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Update
     * @param itemId
     * @param requestBody
     * @returns VectorRecordRead Successful Response
     * @throws ApiError
     */
    public static updateApiV1PublicMemoryVectorRecordsItemIdPut(
        itemId: string,
        requestBody: VectorRecordUpdate,
    ): CancelablePromise<VectorRecordRead> {
        return __request(OpenAPI, {
            method: 'PUT',
            url: '/api/v1/public/memory/vector-records/{item_id}',
            path: {
                'item_id': itemId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Delete
     * @param itemId
     * @returns void
     * @throws ApiError
     */
    public static deleteApiV1PublicMemoryVectorRecordsItemIdDelete(
        itemId: string,
    ): CancelablePromise<void> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/api/v1/public/memory/vector-records/{item_id}',
            path: {
                'item_id': itemId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * List Conversation Topics
     * @param conversationId
     * @returns VectorTopicRead Successful Response
     * @throws ApiError
     */
    public static listConversationTopicsApiV1PublicMemoryConversationsConversationIdTopicsGet(
        conversationId: string,
    ): CancelablePromise<Array<VectorTopicRead>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/public/memory/conversations/{conversation_id}/topics',
            path: {
                'conversation_id': conversationId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Conversation Topic
     * @param conversationId
     * @param topicId
     * @returns VectorTopicDetailRead Successful Response
     * @throws ApiError
     */
    public static getConversationTopicApiV1PublicMemoryConversationsConversationIdTopicsTopicIdGet(
        conversationId: string,
        topicId: string,
    ): CancelablePromise<VectorTopicDetailRead> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/public/memory/conversations/{conversation_id}/topics/{topic_id}',
            path: {
                'conversation_id': conversationId,
                'topic_id': topicId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
