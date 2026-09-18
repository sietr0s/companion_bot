/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { InstagramSettingsCreate } from '../models/InstagramSettingsCreate';
import type { InstagramSettingsRead } from '../models/InstagramSettingsRead';
import type { InstagramSettingsUpdate } from '../models/InstagramSettingsUpdate';
import type { PaginatedResponse_InstagramSettingsRead_ } from '../models/PaginatedResponse_InstagramSettingsRead_';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class InstagramSettingsService {
    /**
     * Get List
     * @param page
     * @param pageSize
     * @param orderBy
     * @returns PaginatedResponse_InstagramSettingsRead_ Successful Response
     * @throws ApiError
     */
    public static getListApiV1PublicInstagramSettingsGet(
        page: number = 1,
        pageSize: number = 100,
        orderBy?: (string | null),
    ): CancelablePromise<PaginatedResponse_InstagramSettingsRead_> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/public/instagram/settings/',
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
     * @returns InstagramSettingsRead Successful Response
     * @throws ApiError
     */
    public static createApiV1PublicInstagramSettingsPost(
        requestBody: InstagramSettingsCreate,
    ): CancelablePromise<InstagramSettingsRead> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/public/instagram/settings/',
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
     * @returns InstagramSettingsRead Successful Response
     * @throws ApiError
     */
    public static getByIdApiV1PublicInstagramSettingsItemIdGet(
        itemId: string,
    ): CancelablePromise<InstagramSettingsRead> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/public/instagram/settings/{item_id}',
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
     * @returns InstagramSettingsRead Successful Response
     * @throws ApiError
     */
    public static updateApiV1PublicInstagramSettingsItemIdPut(
        itemId: string,
        requestBody: InstagramSettingsUpdate,
    ): CancelablePromise<InstagramSettingsRead> {
        return __request(OpenAPI, {
            method: 'PUT',
            url: '/api/v1/public/instagram/settings/{item_id}',
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
    public static deleteApiV1PublicInstagramSettingsItemIdDelete(
        itemId: string,
    ): CancelablePromise<void> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/api/v1/public/instagram/settings/{item_id}',
            path: {
                'item_id': itemId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
