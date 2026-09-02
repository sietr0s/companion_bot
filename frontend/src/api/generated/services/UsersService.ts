/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { PaginatedResponse_UserRead_ } from '../models/PaginatedResponse_UserRead_';
import type { UserCreate } from '../models/UserCreate';
import type { UserRead } from '../models/UserRead';
import type { UserUpdate } from '../models/UserUpdate';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class UsersService {
    /**
     * Get List
     * @param page
     * @param pageSize
     * @param orderBy
     * @returns PaginatedResponse_UserRead_ Successful Response
     * @throws ApiError
     */
    public static getListApiV1PublicUsersGet(
        page: number = 1,
        pageSize: number = 100,
        orderBy?: (string | null),
    ): CancelablePromise<PaginatedResponse_UserRead_> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/public/users/',
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
     * @returns UserRead Successful Response
     * @throws ApiError
     */
    public static createApiV1PublicUsersPost(
        requestBody: UserCreate,
    ): CancelablePromise<UserRead> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/public/users/',
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
     * @returns UserRead Successful Response
     * @throws ApiError
     */
    public static getByIdApiV1PublicUsersItemIdGet(
        itemId: string,
    ): CancelablePromise<UserRead> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/public/users/{item_id}',
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
     * @returns UserRead Successful Response
     * @throws ApiError
     */
    public static updateApiV1PublicUsersItemIdPut(
        itemId: string,
        requestBody: UserUpdate,
    ): CancelablePromise<UserRead> {
        return __request(OpenAPI, {
            method: 'PUT',
            url: '/api/v1/public/users/{item_id}',
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
    public static deleteApiV1PublicUsersItemIdDelete(
        itemId: string,
    ): CancelablePromise<void> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/api/v1/public/users/{item_id}',
            path: {
                'item_id': itemId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
