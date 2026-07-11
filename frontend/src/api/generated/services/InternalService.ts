/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { AuthCreate } from '../models/AuthCreate';
import type { AuthRead } from '../models/AuthRead';
import type { AuthUpdate } from '../models/AuthUpdate';
import type { Body_upload_file_internal_media_upload_post } from '../models/Body_upload_file_internal_media_upload_post';
import type { CategoryRead } from '../models/CategoryRead';
import type { FileRead } from '../models/FileRead';
import type { FileUploadResponse } from '../models/FileUploadResponse';
import type { PaginatedResponse_FileRead_ } from '../models/PaginatedResponse_FileRead_';
import type { PaginatedResponse_UserRead_ } from '../models/PaginatedResponse_UserRead_';
import type { SendNotificationRequest } from '../models/SendNotificationRequest';
import type { src__modules__users__schemas__internal__telegram__TelegramRead } from '../models/src__modules__users__schemas__internal__telegram__TelegramRead';
import type { src__modules__users__schemas__internal__user__UserCreate } from '../models/src__modules__users__schemas__internal__user__UserCreate';
import type { src__modules__users__schemas__internal__user__UserRead } from '../models/src__modules__users__schemas__internal__user__UserRead';
import type { src__modules__users__schemas__internal__user__UserUpdate } from '../models/src__modules__users__schemas__internal__user__UserUpdate';
import type { TelegramCreate } from '../models/TelegramCreate';
import type { TelegramSettingsCreate } from '../models/TelegramSettingsCreate';
import type { TelegramSettingsRead } from '../models/TelegramSettingsRead';
import type { TelegramSettingsUpdate } from '../models/TelegramSettingsUpdate';
import type { VerifyTokenRequest } from '../models/VerifyTokenRequest';
import type { VerifyTokenResponse } from '../models/VerifyTokenResponse';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class InternalService {
    /**
     * [Internal] Создать учётную запись
     * Создать учётную запись (internal, без JWT).
     * @param requestBody
     * @returns AuthRead Successful Response
     * @throws ApiError
     */
    public static createAccountInternalAuthPost(
        requestBody: AuthCreate,
    ): CancelablePromise<AuthRead> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/internal/auth/',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * [Internal] Получить учётную запись по auth_id
     * Получить учётную запись по auth_id (internal).
     * @param authId
     * @returns AuthRead Successful Response
     * @throws ApiError
     */
    public static getAccountInternalAuthAuthIdGet(
        authId: string,
    ): CancelablePromise<AuthRead> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/internal/auth/{auth_id}',
            path: {
                'auth_id': authId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * [Internal] Обновить учётную запись
     * Обновить учётную запись (internal).
     * @param authId
     * @param requestBody
     * @returns AuthRead Successful Response
     * @throws ApiError
     */
    public static updateAccountInternalAuthAuthIdPatch(
        authId: string,
        requestBody: AuthUpdate,
    ): CancelablePromise<AuthRead> {
        return __request(OpenAPI, {
            method: 'PATCH',
            url: '/internal/auth/{auth_id}',
            path: {
                'auth_id': authId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * [Internal] Удалить учётную запись
     * Удалить учётную запись (internal, без проверки пароля).
     * @param authId
     * @returns void
     * @throws ApiError
     */
    public static deleteAccountInternalAuthAuthIdDelete(
        authId: string,
    ): CancelablePromise<void> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/internal/auth/{auth_id}',
            path: {
                'auth_id': authId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * [Internal] Проверить валидность токена
     * Проверить валидность JWT токена (internal).
     * @param requestBody
     * @returns VerifyTokenResponse Successful Response
     * @throws ApiError
     */
    public static verifyTokenInternalAuthVerifyPost(
        requestBody: VerifyTokenRequest,
    ): CancelablePromise<VerifyTokenResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/internal/auth/verify',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * [Internal] Получить пользователей с фильтрацией
     * Внутренний эндпоинт для межмодульного взаимодействия.
     *
     * Фильтры: `filters=field+eq+value`.
     * Операторы: eq, ne, gt, ge, lt, le, like, ilike, in.
     * @param filters field+operator+value
     * @param page
     * @param limit
     * @returns PaginatedResponse_UserRead_ Successful Response
     * @throws ApiError
     */
    public static getUsersInternalUsersGet(
        filters?: Array<string>,
        page: number = 1,
        limit: number = 100,
    ): CancelablePromise<PaginatedResponse_UserRead_> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/internal/users/',
            query: {
                'filters': filters,
                'page': page,
                'limit': limit,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * [Internal] Создать профиль пользователя
     * Создать профиль пользователя (internal, без JWT).
     * @param requestBody
     * @returns src__modules__users__schemas__internal__user__UserRead Successful Response
     * @throws ApiError
     */
    public static createProfileInternalInternalUsersPost(
        requestBody: src__modules__users__schemas__internal__user__UserCreate,
    ): CancelablePromise<src__modules__users__schemas__internal__user__UserRead> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/internal/users/',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * [Internal] Получить профиль по id
     * Получить профиль по id (internal).
     * @param profileId
     * @returns src__modules__users__schemas__internal__user__UserRead Successful Response
     * @throws ApiError
     */
    public static getProfileInternalInternalUsersProfileIdGet(
        profileId: string,
    ): CancelablePromise<src__modules__users__schemas__internal__user__UserRead> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/internal/users/{profile_id}',
            path: {
                'profile_id': profileId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * [Internal] Обновить профиль
     * Обновить профиль (internal).
     * @param profileId
     * @param requestBody
     * @returns src__modules__users__schemas__internal__user__UserRead Successful Response
     * @throws ApiError
     */
    public static updateProfileInternalInternalUsersProfileIdPatch(
        profileId: string,
        requestBody: src__modules__users__schemas__internal__user__UserUpdate,
    ): CancelablePromise<src__modules__users__schemas__internal__user__UserRead> {
        return __request(OpenAPI, {
            method: 'PATCH',
            url: '/internal/users/{profile_id}',
            path: {
                'profile_id': profileId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * [Internal] Удалить профиль
     * Удалить профиль (internal, без проверки JWT).
     * @param profileId
     * @returns void
     * @throws ApiError
     */
    public static deleteProfileInternalInternalUsersProfileIdDelete(
        profileId: string,
    ): CancelablePromise<void> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/internal/users/{profile_id}',
            path: {
                'profile_id': profileId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * [Internal] Создать Telegram профиль
     * Создать Telegram профиль и связать с пользователем (internal).
     * @param profileId
     * @param requestBody
     * @returns src__modules__users__schemas__internal__telegram__TelegramRead Successful Response
     * @throws ApiError
     */
    public static createTelegramProfileInternalUsersProfileIdTelegramPost(
        profileId: string,
        requestBody: TelegramCreate,
    ): CancelablePromise<src__modules__users__schemas__internal__telegram__TelegramRead> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/internal/users/{profile_id}/telegram',
            path: {
                'profile_id': profileId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * [Internal] Отправить уведомление по шаблону
     * Отправить уведомление по имени шаблона.
     *
     * Используется для межмодульного взаимодействия.
     * @param requestBody
     * @returns SendNotificationRequest Successful Response
     * @throws ApiError
     */
    public static sendNotificationInternalNotificationsSendPost(
        requestBody: SendNotificationRequest,
    ): CancelablePromise<SendNotificationRequest> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/internal/notifications/send',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * [Internal] Тестовый рендер шаблона
     * Тестовый рендер шаблона с данными.
     *
     * Возвращает rendered subject и body без отправки.
     * @param templateId
     * @param requestBody
     * @returns any Successful Response
     * @throws ApiError
     */
    public static renderTemplateTestInternalNotificationsTemplatesTemplateIdRenderPost(
        templateId: string,
        requestBody?: Record<string, any>,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/internal/notifications/templates/{template_id}/render',
            path: {
                'template_id': templateId,
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
     * Получить настройки Telegram-аккаунта.
     * @param accountId
     * @returns TelegramSettingsRead Successful Response
     * @throws ApiError
     */
    public static getSettingsInternalTelegramAccountIdSettingsGet(
        accountId: string,
    ): CancelablePromise<TelegramSettingsRead> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/internal/telegram/{account_id}/settings',
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
     * Создать настройки Telegram-аккаунта.
     * @param accountId
     * @param requestBody
     * @returns TelegramSettingsRead Successful Response
     * @throws ApiError
     */
    public static createSettingsInternalTelegramAccountIdSettingsPost(
        accountId: string,
        requestBody: TelegramSettingsCreate,
    ): CancelablePromise<TelegramSettingsRead> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/internal/telegram/{account_id}/settings',
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
     * Обновить настройки Telegram-аккаунта.
     * @param accountId
     * @param requestBody
     * @returns TelegramSettingsRead Successful Response
     * @throws ApiError
     */
    public static updateSettingsInternalTelegramAccountIdSettingsPut(
        accountId: string,
        requestBody: TelegramSettingsUpdate,
    ): CancelablePromise<TelegramSettingsRead> {
        return __request(OpenAPI, {
            method: 'PUT',
            url: '/internal/telegram/{account_id}/settings',
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
     * Delete Settings
     * Удалить настройки Telegram-аккаунта.
     * @param accountId
     * @returns void
     * @throws ApiError
     */
    public static deleteSettingsInternalTelegramAccountIdSettingsDelete(
        accountId: string,
    ): CancelablePromise<void> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/internal/telegram/{account_id}/settings',
            path: {
                'account_id': accountId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * [Internal] Список всех файлов
     * Получить список всех файлов с фильтрацией и пагинацией (internal).
     * @param filters field+operator+value
     * @param page
     * @param limit
     * @returns PaginatedResponse_FileRead_ Successful Response
     * @throws ApiError
     */
    public static listFilesInternalInternalMediaGet(
        filters?: Array<string>,
        page: number = 1,
        limit: number = 100,
    ): CancelablePromise<PaginatedResponse_FileRead_> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/internal/media/',
            query: {
                'filters': filters,
                'page': page,
                'limit': limit,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * [Internal] Загрузить файл
     * Загрузить файл (без JWT, network-level доступ).
     * @param formData
     * @returns FileUploadResponse Successful Response
     * @throws ApiError
     */
    public static uploadFileInternalMediaUploadPost(
        formData: Body_upload_file_internal_media_upload_post,
    ): CancelablePromise<FileUploadResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/internal/media/upload',
            formData: formData,
            mediaType: 'multipart/form-data',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * [Internal] Метаданные файла
     * Метаданные любого файла (включая приватные).
     * @param fileId
     * @returns FileRead Successful Response
     * @throws ApiError
     */
    public static getFileInternalMediaFileIdGet(
        fileId: string,
    ): CancelablePromise<FileRead> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/internal/media/{file_id}',
            path: {
                'file_id': fileId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * [Internal] Удалить файл
     * Удалить файл (без JWT).
     * @param fileId
     * @returns void
     * @throws ApiError
     */
    public static deleteFileInternalMediaFileIdDelete(
        fileId: string,
    ): CancelablePromise<void> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/internal/media/{file_id}',
            path: {
                'file_id': fileId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * [Internal] Скачать файл
     * Скачать любой файл (потоком, включая приватные).
     * @param fileId
     * @returns any Successful Response
     * @throws ApiError
     */
    public static downloadFileInternalMediaFileIdDownloadGet(
        fileId: string,
    ): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/internal/media/{file_id}/download',
            path: {
                'file_id': fileId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * [Internal] Список категорий
     * Получить список всех категорий для внутреннего использования.
     * @returns CategoryRead Successful Response
     * @throws ApiError
     */
    public static getCategoriesInternalClassifierInternalClassifierCategoriesGet(): CancelablePromise<Array<CategoryRead>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/internal/classifier/internal/classifier/categories',
        });
    }
}
