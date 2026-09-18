/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ChatStateCreate } from '../models/ChatStateCreate';
import type { ChatStateRead } from '../models/ChatStateRead';
import type { ChatStateUpdate } from '../models/ChatStateUpdate';
import type { PaginatedResponse_ChatStateRead_ } from '../models/PaginatedResponse_ChatStateRead_';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class TelegramChatStatesService {
    /**
     * Get List
     * @param page
     * @param pageSize
     * @param orderBy
     * @returns PaginatedResponse_ChatStateRead_ Successful Response
     * @throws ApiError
     */
    public static getListApiV1PublicTelegramChatStatesGet(
        page: number = 1,
        pageSize: number = 100,
        orderBy?: (string | null),
    ): CancelablePromise<PaginatedResponse_ChatStateRead_> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/public/telegram/chat-states/',
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
     * @returns ChatStateRead Successful Response
     * @throws ApiError
     */
    public static createApiV1PublicTelegramChatStatesPost(
        requestBody: ChatStateCreate,
    ): CancelablePromise<ChatStateRead> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/public/telegram/chat-states/',
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
     * @returns ChatStateRead Successful Response
     * @throws ApiError
     */
    public static getByIdApiV1PublicTelegramChatStatesItemIdGet(
        itemId: string,
    ): CancelablePromise<ChatStateRead> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/public/telegram/chat-states/{item_id}',
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
     * @returns ChatStateRead Successful Response
     * @throws ApiError
     */
    public static updateApiV1PublicTelegramChatStatesItemIdPut(
        itemId: string,
        requestBody: ChatStateUpdate,
    ): CancelablePromise<ChatStateRead> {
        return __request(OpenAPI, {
            method: 'PUT',
            url: '/api/v1/public/telegram/chat-states/{item_id}',
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
    public static deleteApiV1PublicTelegramChatStatesItemIdDelete(
        itemId: string,
    ): CancelablePromise<void> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/api/v1/public/telegram/chat-states/{item_id}',
            path: {
                'item_id': itemId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
