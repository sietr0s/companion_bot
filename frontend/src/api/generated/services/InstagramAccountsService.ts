/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { InstagramAccountCreate } from '../models/InstagramAccountCreate';
import type { InstagramAccountRead } from '../models/InstagramAccountRead';
import type { InstagramAccountUpdate } from '../models/InstagramAccountUpdate';
import type { PaginatedResponse_InstagramAccountRead_ } from '../models/PaginatedResponse_InstagramAccountRead_';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class InstagramAccountsService {
    /**
     * Get List
     * @param page
     * @param pageSize
     * @param orderBy
     * @returns PaginatedResponse_InstagramAccountRead_ Successful Response
     * @throws ApiError
     */
    public static getListApiV1PublicInstagramAccountsGet(
        page: number = 1,
        pageSize: number = 100,
        orderBy?: (string | null),
    ): CancelablePromise<PaginatedResponse_InstagramAccountRead_> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/public/instagram/accounts/',
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
     * @returns InstagramAccountRead Successful Response
     * @throws ApiError
     */
    public static createApiV1PublicInstagramAccountsPost(
        requestBody: InstagramAccountCreate,
    ): CancelablePromise<InstagramAccountRead> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/public/instagram/accounts/',
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
     * @returns InstagramAccountRead Successful Response
     * @throws ApiError
     */
    public static getByIdApiV1PublicInstagramAccountsItemIdGet(
        itemId: string,
    ): CancelablePromise<InstagramAccountRead> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/public/instagram/accounts/{item_id}',
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
     * @returns InstagramAccountRead Successful Response
     * @throws ApiError
     */
    public static updateApiV1PublicInstagramAccountsItemIdPut(
        itemId: string,
        requestBody: InstagramAccountUpdate,
    ): CancelablePromise<InstagramAccountRead> {
        return __request(OpenAPI, {
            method: 'PUT',
            url: '/api/v1/public/instagram/accounts/{item_id}',
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
    public static deleteApiV1PublicInstagramAccountsItemIdDelete(
        itemId: string,
    ): CancelablePromise<void> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/api/v1/public/instagram/accounts/{item_id}',
            path: {
                'item_id': itemId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
