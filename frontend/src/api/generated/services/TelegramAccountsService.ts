/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { AccountCreate } from '../models/AccountCreate';
import type { AccountRead } from '../models/AccountRead';
import type { AccountUpdate } from '../models/AccountUpdate';
import type { PaginatedResponse_AccountRead_ } from '../models/PaginatedResponse_AccountRead_';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class TelegramAccountsService {
    /**
     * Get List
     * @param page
     * @param pageSize
     * @param orderBy
     * @returns PaginatedResponse_AccountRead_ Successful Response
     * @throws ApiError
     */
    public static getListApiV1PublicTelegramAccountsGet(
        page: number = 1,
        pageSize: number = 100,
        orderBy?: (string | null),
    ): CancelablePromise<PaginatedResponse_AccountRead_> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/public/telegram/accounts/',
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
     * @returns AccountRead Successful Response
     * @throws ApiError
     */
    public static createApiV1PublicTelegramAccountsPost(
        requestBody: AccountCreate,
    ): CancelablePromise<AccountRead> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/public/telegram/accounts/',
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
     * @returns AccountRead Successful Response
     * @throws ApiError
     */
    public static getByIdApiV1PublicTelegramAccountsItemIdGet(
        itemId: string,
    ): CancelablePromise<AccountRead> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/public/telegram/accounts/{item_id}',
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
     * @returns AccountRead Successful Response
     * @throws ApiError
     */
    public static updateApiV1PublicTelegramAccountsItemIdPut(
        itemId: string,
        requestBody: AccountUpdate,
    ): CancelablePromise<AccountRead> {
        return __request(OpenAPI, {
            method: 'PUT',
            url: '/api/v1/public/telegram/accounts/{item_id}',
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
    public static deleteApiV1PublicTelegramAccountsItemIdDelete(
        itemId: string,
    ): CancelablePromise<void> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/api/v1/public/telegram/accounts/{item_id}',
            path: {
                'item_id': itemId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
