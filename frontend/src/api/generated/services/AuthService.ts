/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { AuthAccountCreate } from '../models/AuthAccountCreate';
import type { AuthAccountRead } from '../models/AuthAccountRead';
import type { AuthAccountUpdate } from '../models/AuthAccountUpdate';
import type { LoginRequest } from '../models/LoginRequest';
import type { PaginatedResponse_AuthAccountRead_ } from '../models/PaginatedResponse_AuthAccountRead_';
import type { RegisterRequest } from '../models/RegisterRequest';
import type { TokenResponse } from '../models/TokenResponse';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class AuthService {
    /**
     * Регистрация нового пользователя
     * @param requestBody
     * @returns TokenResponse Successful Response
     * @throws ApiError
     */
    public static registerApiV1PublicAuthRegisterPost(
        requestBody: RegisterRequest,
    ): CancelablePromise<TokenResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/public/auth/register',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Авторизация пользователя
     * @param requestBody
     * @returns TokenResponse Successful Response
     * @throws ApiError
     */
    public static loginApiV1PublicAuthLoginPost(
        requestBody: LoginRequest,
    ): CancelablePromise<TokenResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/public/auth/login',
            body: requestBody,
            mediaType: 'application/json',
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
     * @returns PaginatedResponse_AuthAccountRead_ Successful Response
     * @throws ApiError
     */
    public static getListApiV1PublicAuthAccountsGet(
        page: number = 1,
        pageSize: number = 100,
        orderBy?: (string | null),
    ): CancelablePromise<PaginatedResponse_AuthAccountRead_> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/public/auth/accounts/',
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
     * @returns AuthAccountRead Successful Response
     * @throws ApiError
     */
    public static createApiV1PublicAuthAccountsPost(
        requestBody: AuthAccountCreate,
    ): CancelablePromise<AuthAccountRead> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/public/auth/accounts/',
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
     * @returns AuthAccountRead Successful Response
     * @throws ApiError
     */
    public static getByIdApiV1PublicAuthAccountsItemIdGet(
        itemId: string,
    ): CancelablePromise<AuthAccountRead> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/public/auth/accounts/{item_id}',
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
     * @returns AuthAccountRead Successful Response
     * @throws ApiError
     */
    public static updateApiV1PublicAuthAccountsItemIdPut(
        itemId: string,
        requestBody: AuthAccountUpdate,
    ): CancelablePromise<AuthAccountRead> {
        return __request(OpenAPI, {
            method: 'PUT',
            url: '/api/v1/public/auth/accounts/{item_id}',
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
    public static deleteApiV1PublicAuthAccountsItemIdDelete(
        itemId: string,
    ): CancelablePromise<void> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/api/v1/public/auth/accounts/{item_id}',
            path: {
                'item_id': itemId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
