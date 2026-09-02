/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { AccountCreate } from '../models/AccountCreate';
import type { AccountRead } from '../models/AccountRead';
import type { AccountUpdate } from '../models/AccountUpdate';
import type { AuthStep1Response } from '../models/AuthStep1Response';
import type { AuthStep2Response } from '../models/AuthStep2Response';
import type { AuthStep3Response } from '../models/AuthStep3Response';
import type { ChatRead } from '../models/ChatRead';
import type { ChatStateCreate } from '../models/ChatStateCreate';
import type { ChatStateRead } from '../models/ChatStateRead';
import type { ChatStateUpdate } from '../models/ChatStateUpdate';
import type { CodeRequest } from '../models/CodeRequest';
import type { MessageRead } from '../models/MessageRead';
import type { PaginatedResponse_AccountRead_ } from '../models/PaginatedResponse_AccountRead_';
import type { PaginatedResponse_ChatStateRead_ } from '../models/PaginatedResponse_ChatStateRead_';
import type { PaginatedResponse_TelegramSettingsRead_ } from '../models/PaginatedResponse_TelegramSettingsRead_';
import type { PasswordRequest } from '../models/PasswordRequest';
import type { PhoneRequest } from '../models/PhoneRequest';
import type { QrStartResponse } from '../models/QrStartResponse';
import type { QrStatusResponse } from '../models/QrStatusResponse';
import type { TelegramSettingsCreate } from '../models/TelegramSettingsCreate';
import type { TelegramSettingsRead } from '../models/TelegramSettingsRead';
import type { TelegramSettingsUpdate } from '../models/TelegramSettingsUpdate';
import type { WhitelistEntryCreate } from '../models/WhitelistEntryCreate';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class TelegramClientsService {
    /**
     * Шаг 1: отправить номер телефона
     * @param requestBody
     * @returns AuthStep1Response Successful Response
     * @throws ApiError
     */
    public static authPhoneApiV1PublicTelegramAuthPhonePost(
        requestBody: PhoneRequest,
    ): CancelablePromise<AuthStep1Response> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/public/telegram/auth/phone',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Шаг 2: ввести SMS-код
     * @param requestBody
     * @returns AuthStep2Response Successful Response
     * @throws ApiError
     */
    public static authCodeApiV1PublicTelegramAuthCodePost(
        requestBody: CodeRequest,
    ): CancelablePromise<AuthStep2Response> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/public/telegram/auth/code',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Шаг 3: ввести пароль 2FA
     * @param requestBody
     * @returns AuthStep3Response Successful Response
     * @throws ApiError
     */
    public static authPasswordApiV1PublicTelegramAuthPasswordPost(
        requestBody: PasswordRequest,
    ): CancelablePromise<AuthStep3Response> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/public/telegram/auth/password',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Запустить QR-авторизацию Telegram
     * @returns QrStartResponse Successful Response
     * @throws ApiError
     */
    public static authQrStartApiV1PublicTelegramAuthQrPost(): CancelablePromise<QrStartResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/public/telegram/auth/qr',
        });
    }
    /**
     * Статус QR-авторизации
     * @param accountId
     * @returns QrStatusResponse Successful Response
     * @throws ApiError
     */
    public static authQrStatusApiV1PublicTelegramAuthQrAccountIdStatusGet(
        accountId: string,
    ): CancelablePromise<QrStatusResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/public/telegram/auth/qr/{account_id}/status',
            path: {
                'account_id': accountId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Отменить QR-авторизацию
     * @param accountId
     * @returns void
     * @throws ApiError
     */
    public static authQrCancelApiV1PublicTelegramAuthQrAccountIdDelete(
        accountId: string,
    ): CancelablePromise<void> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/api/v1/public/telegram/auth/qr/{account_id}',
            path: {
                'account_id': accountId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Завершить QR-авторизацию
     * @param accountId
     * @returns AccountRead Successful Response
     * @throws ApiError
     */
    public static authQrCompleteApiV1PublicTelegramAuthQrAccountIdCompletePost(
        accountId: string,
    ): CancelablePromise<AccountRead> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/public/telegram/auth/qr/{account_id}/complete',
            path: {
                'account_id': accountId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Список Telegram-аккаунтов
     * @param filters field+operator+value
     * @param page
     * @param limit
     * @param orderBy Поле сортировки; '-' = DESC
     * @returns PaginatedResponse_AccountRead_ Successful Response
     * @throws ApiError
     */
    public static getAccountsApiV1PublicTelegramGet(
        filters?: Array<string>,
        page: number = 1,
        limit: number = 100,
        orderBy: string = '-created_at',
    ): CancelablePromise<PaginatedResponse_AccountRead_> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/public/telegram/',
            query: {
                'filters': filters,
                'page': page,
                'limit': limit,
                'order_by': orderBy,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Telegram-аккаунт
     * @param accountId
     * @returns AccountRead Successful Response
     * @throws ApiError
     */
    public static getAccountApiV1PublicTelegramAccountIdGet(
        accountId: string,
    ): CancelablePromise<AccountRead> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/public/telegram/{account_id}',
            path: {
                'account_id': accountId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Удалить Telegram-аккаунт
     * @param accountId
     * @returns void
     * @throws ApiError
     */
    public static deleteAccountApiV1PublicTelegramAccountIdDelete(
        accountId: string,
    ): CancelablePromise<void> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/api/v1/public/telegram/{account_id}',
            path: {
                'account_id': accountId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Список чатов аккаунта
     * @param accountId
     * @param limit
     * @returns ChatRead Successful Response
     * @throws ApiError
     */
    public static getChatsApiV1PublicTelegramAccountIdChatsGet(
        accountId: string,
        limit: number = 100,
    ): CancelablePromise<Array<ChatRead>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/public/telegram/{account_id}/chats',
            path: {
                'account_id': accountId,
            },
            query: {
                'limit': limit,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Сообщения чата
     * @param accountId
     * @param chatId
     * @param limit
     * @param offsetId
     * @returns MessageRead Successful Response
     * @throws ApiError
     */
    public static getMessagesApiV1PublicTelegramAccountIdChatsChatIdMessagesGet(
        accountId: string,
        chatId: number,
        limit: number = 50,
        offsetId?: number,
    ): CancelablePromise<Array<MessageRead>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/public/telegram/{account_id}/chats/{chat_id}/messages',
            path: {
                'account_id': accountId,
                'chat_id': chatId,
            },
            query: {
                'limit': limit,
                'offset_id': offsetId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Настройки чтения аккаунта
     * @param accountId
     * @returns TelegramSettingsRead Successful Response
     * @throws ApiError
     */
    public static getSettingsApiV1PublicTelegramAccountIdSettingsGet(
        accountId: string,
    ): CancelablePromise<TelegramSettingsRead> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/public/telegram/{account_id}/settings',
            path: {
                'account_id': accountId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Создать настройки чтения
     * @param accountId
     * @param requestBody
     * @returns TelegramSettingsRead Successful Response
     * @throws ApiError
     */
    public static createSettingsApiV1PublicTelegramAccountIdSettingsPost(
        accountId: string,
        requestBody: TelegramSettingsCreate,
    ): CancelablePromise<TelegramSettingsRead> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/public/telegram/{account_id}/settings',
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
     * Обновить настройки чтения
     * @param accountId
     * @param requestBody
     * @returns TelegramSettingsRead Successful Response
     * @throws ApiError
     */
    public static updateSettingsApiV1PublicTelegramAccountIdSettingsPut(
        accountId: string,
        requestBody: TelegramSettingsUpdate,
    ): CancelablePromise<TelegramSettingsRead> {
        return __request(OpenAPI, {
            method: 'PUT',
            url: '/api/v1/public/telegram/{account_id}/settings',
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
     * Удалить настройки чтения
     * @param accountId
     * @returns void
     * @throws ApiError
     */
    public static deleteSettingsApiV1PublicTelegramAccountIdSettingsDelete(
        accountId: string,
    ): CancelablePromise<void> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/api/v1/public/telegram/{account_id}/settings',
            path: {
                'account_id': accountId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Add Chat To Whitelist
     * @param accountId
     * @param requestBody
     * @returns TelegramSettingsRead Successful Response
     * @throws ApiError
     */
    public static addChatToWhitelistApiV1PublicTelegramAccountIdWhitelistPost(
        accountId: string,
        requestBody: WhitelistEntryCreate,
    ): CancelablePromise<TelegramSettingsRead> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/public/telegram/{account_id}/whitelist',
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
     * Remove Chat From Whitelist
     * @param accountId
     * @param chatId
     * @returns TelegramSettingsRead Successful Response
     * @throws ApiError
     */
    public static removeChatFromWhitelistApiV1PublicTelegramAccountIdWhitelistChatIdDelete(
        accountId: string,
        chatId: number,
    ): CancelablePromise<TelegramSettingsRead> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/api/v1/public/telegram/{account_id}/whitelist/{chat_id}',
            path: {
                'account_id': accountId,
                'chat_id': chatId,
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
