/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { InstagramChatStateCreate } from '../models/InstagramChatStateCreate';
import type { InstagramChatStateRead } from '../models/InstagramChatStateRead';
import type { InstagramChatStateUpdate } from '../models/InstagramChatStateUpdate';
import type { PaginatedResponse_InstagramChatStateRead_ } from '../models/PaginatedResponse_InstagramChatStateRead_';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class InstagramChatStatesService {
    /**
     * Get List
     * @param page
     * @param pageSize
     * @param orderBy
     * @returns PaginatedResponse_InstagramChatStateRead_ Successful Response
     * @throws ApiError
     */
    public static getListApiV1PublicInstagramChatStatesGet(
        page: number = 1,
        pageSize: number = 100,
        orderBy?: (string | null),
    ): CancelablePromise<PaginatedResponse_InstagramChatStateRead_> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/public/instagram/chat-states/',
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
     * @returns InstagramChatStateRead Successful Response
     * @throws ApiError
     */
    public static createApiV1PublicInstagramChatStatesPost(
        requestBody: InstagramChatStateCreate,
    ): CancelablePromise<InstagramChatStateRead> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/public/instagram/chat-states/',
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
     * @returns InstagramChatStateRead Successful Response
     * @throws ApiError
     */
    public static getByIdApiV1PublicInstagramChatStatesItemIdGet(
        itemId: string,
    ): CancelablePromise<InstagramChatStateRead> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/public/instagram/chat-states/{item_id}',
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
     * @returns InstagramChatStateRead Successful Response
     * @throws ApiError
     */
    public static updateApiV1PublicInstagramChatStatesItemIdPut(
        itemId: string,
        requestBody: InstagramChatStateUpdate,
    ): CancelablePromise<InstagramChatStateRead> {
        return __request(OpenAPI, {
            method: 'PUT',
            url: '/api/v1/public/instagram/chat-states/{item_id}',
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
    public static deleteApiV1PublicInstagramChatStatesItemIdDelete(
        itemId: string,
    ): CancelablePromise<void> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/api/v1/public/instagram/chat-states/{item_id}',
            path: {
                'item_id': itemId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
