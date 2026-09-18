/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { InstagramAccountCreate } from '../models/InstagramAccountCreate';
import type { InstagramAccountRead } from '../models/InstagramAccountRead';
import type { InstagramAccountUpdate } from '../models/InstagramAccountUpdate';
import type { InstagramChatStateCreate } from '../models/InstagramChatStateCreate';
import type { InstagramChatStateRead } from '../models/InstagramChatStateRead';
import type { InstagramChatStateUpdate } from '../models/InstagramChatStateUpdate';
import type { InstagramCodeRequest } from '../models/InstagramCodeRequest';
import type { InstagramLoginRequest } from '../models/InstagramLoginRequest';
import type { InstagramSettingsCreate } from '../models/InstagramSettingsCreate';
import type { InstagramSettingsRead } from '../models/InstagramSettingsRead';
import type { InstagramSettingsUpdate } from '../models/InstagramSettingsUpdate';
import type { InstagramWhitelistEntryCreate } from '../models/InstagramWhitelistEntryCreate';
import type { PaginatedResponse_InstagramAccountRead_ } from '../models/PaginatedResponse_InstagramAccountRead_';
import type { PaginatedResponse_InstagramChatStateRead_ } from '../models/PaginatedResponse_InstagramChatStateRead_';
import type { PaginatedResponse_InstagramSettingsRead_ } from '../models/PaginatedResponse_InstagramSettingsRead_';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class InstagramClientsService {
    /**
     * Login
     * @param accountId
     * @param requestBody
     * @returns InstagramAccountRead Successful Response
     * @throws ApiError
     */
    public static loginApiV1PublicInstagramAccountsAccountIdLoginPost(
        accountId: string,
        requestBody: InstagramLoginRequest,
    ): CancelablePromise<InstagramAccountRead> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/public/instagram/accounts/{account_id}/login',
            path: {
                'account_id': accountId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Two Factor
     * @param accountId
     * @param requestBody
     * @returns InstagramAccountRead Successful Response
     * @throws ApiError
     */
    public static twoFactorApiV1PublicInstagramAccountsAccountIdTwoFactorPost(
        accountId: string,
        requestBody: InstagramCodeRequest,
    ): CancelablePromise<InstagramAccountRead> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/public/instagram/accounts/{account_id}/two-factor',
            path: {
                'account_id': accountId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Challenge
     * @param accountId
     * @param requestBody
     * @returns InstagramAccountRead Successful Response
     * @throws ApiError
     */
    public static challengeApiV1PublicInstagramAccountsAccountIdChallengePost(
        accountId: string,
        requestBody: InstagramCodeRequest,
    ): CancelablePromise<InstagramAccountRead> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/public/instagram/accounts/{account_id}/challenge',
            path: {
                'account_id': accountId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Settings
     * @param accountId
     * @returns InstagramSettingsRead Successful Response
     * @throws ApiError
     */
    public static getSettingsApiV1PublicInstagramAccountIdSettingsGet(
        accountId: string,
    ): CancelablePromise<InstagramSettingsRead> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/public/instagram/{account_id}/settings',
            path: {
                'account_id': accountId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Create Settings
     * @param accountId
     * @param requestBody
     * @returns InstagramSettingsRead Successful Response
     * @throws ApiError
     */
    public static createSettingsApiV1PublicInstagramAccountIdSettingsPost(
        accountId: string,
        requestBody: InstagramSettingsCreate,
    ): CancelablePromise<InstagramSettingsRead> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/public/instagram/{account_id}/settings',
            path: {
                'account_id': accountId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Update Settings
     * @param accountId
     * @param requestBody
     * @returns InstagramSettingsRead Successful Response
     * @throws ApiError
     */
    public static updateSettingsApiV1PublicInstagramAccountIdSettingsPut(
        accountId: string,
        requestBody: InstagramSettingsUpdate,
    ): CancelablePromise<InstagramSettingsRead> {
        return __request(OpenAPI, {
            method: 'PUT',
            url: '/api/v1/public/instagram/{account_id}/settings',
            path: {
                'account_id': accountId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Add User To Whitelist
     * @param accountId
     * @param requestBody
     * @returns InstagramSettingsRead Successful Response
     * @throws ApiError
     */
    public static addUserToWhitelistApiV1PublicInstagramAccountIdWhitelistPost(
        accountId: string,
        requestBody: InstagramWhitelistEntryCreate,
    ): CancelablePromise<InstagramSettingsRead> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/public/instagram/{account_id}/whitelist',
            path: {
                'account_id': accountId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Remove User From Whitelist
     * @param accountId
     * @param userPk
     * @returns InstagramSettingsRead Successful Response
     * @throws ApiError
     */
    public static removeUserFromWhitelistApiV1PublicInstagramAccountIdWhitelistUserPkDelete(
        accountId: string,
        userPk: number,
    ): CancelablePromise<InstagramSettingsRead> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/api/v1/public/instagram/{account_id}/whitelist/{user_pk}',
            path: {
                'account_id': accountId,
                'user_pk': userPk,
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
