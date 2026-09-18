/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { PaginatedResponse_TelegramSettingsRead_ } from '../models/PaginatedResponse_TelegramSettingsRead_';
import type { TelegramSettingsCreate } from '../models/TelegramSettingsCreate';
import type { TelegramSettingsRead } from '../models/TelegramSettingsRead';
import type { TelegramSettingsUpdate } from '../models/TelegramSettingsUpdate';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class TelegramSettingsService {
    /**
     * Get List
     * @param page
     * @param pageSize
     * @param orderBy
     * @returns PaginatedResponse_TelegramSettingsRead_ Successful Response
     * @throws ApiError
     */
    public static getListApiV1PublicTelegramSettingsGet(
        page: number = 1,
        pageSize: number = 100,
        orderBy?: (string | null),
    ): CancelablePromise<PaginatedResponse_TelegramSettingsRead_> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/public/telegram/settings/',
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
     * @returns TelegramSettingsRead Successful Response
     * @throws ApiError
     */
    public static createApiV1PublicTelegramSettingsPost(
        requestBody: TelegramSettingsCreate,
    ): CancelablePromise<TelegramSettingsRead> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/public/telegram/settings/',
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
     * @returns TelegramSettingsRead Successful Response
     * @throws ApiError
     */
    public static getByIdApiV1PublicTelegramSettingsItemIdGet(
        itemId: string,
    ): CancelablePromise<TelegramSettingsRead> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/public/telegram/settings/{item_id}',
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
     * @returns TelegramSettingsRead Successful Response
     * @throws ApiError
     */
    public static updateApiV1PublicTelegramSettingsItemIdPut(
        itemId: string,
        requestBody: TelegramSettingsUpdate,
    ): CancelablePromise<TelegramSettingsRead> {
        return __request(OpenAPI, {
            method: 'PUT',
            url: '/api/v1/public/telegram/settings/{item_id}',
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
    public static deleteApiV1PublicTelegramSettingsItemIdDelete(
        itemId: string,
    ): CancelablePromise<void> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/api/v1/public/telegram/settings/{item_id}',
            path: {
                'item_id': itemId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
