/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { src__modules__users__schemas__public__telegram__TelegramRead } from '../models/src__modules__users__schemas__public__telegram__TelegramRead';
import type { src__modules__users__schemas__public__user__UserCreate } from '../models/src__modules__users__schemas__public__user__UserCreate';
import type { src__modules__users__schemas__public__user__UserRead } from '../models/src__modules__users__schemas__public__user__UserRead';
import type { src__modules__users__schemas__public__user__UserUpdate } from '../models/src__modules__users__schemas__public__user__UserUpdate';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class UsersService {
    /**
     * Создание профиля пользователя
     * Создаёт профиль пользователя.
     *
     * auth_id берётся из JWT-токена (авторизованный пользователь).
     * В теле запроса можно передать first_name, last_name и т.д.
     * @param requestBody
     * @returns src__modules__users__schemas__public__user__UserRead Successful Response
     * @throws ApiError
     */
    public static createProfileApiV1PublicUsersPost(
        requestBody: src__modules__users__schemas__public__user__UserCreate,
    ): CancelablePromise<src__modules__users__schemas__public__user__UserRead> {
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
     * Получение профиля текущего пользователя
     * Возвращает профиль авторизованного пользователя.
     * @returns src__modules__users__schemas__public__user__UserRead Successful Response
     * @throws ApiError
     */
    public static getMeApiV1PublicUsersMeGet(): CancelablePromise<src__modules__users__schemas__public__user__UserRead> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/public/users/me',
        });
    }
    /**
     * Удаление профиля текущего пользователя
     * Удаляет профиль авторизованного пользователя.
     * @returns void
     * @throws ApiError
     */
    public static deleteMeApiV1PublicUsersMeDelete(): CancelablePromise<void> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/api/v1/public/users/me',
        });
    }
    /**
     * Обновление профиля текущего пользователя
     * Обновляет профиль авторизованного пользователя (partial update).
     * @param requestBody
     * @returns src__modules__users__schemas__public__user__UserRead Successful Response
     * @throws ApiError
     */
    public static updateMeApiV1PublicUsersMePatch(
        requestBody: src__modules__users__schemas__public__user__UserUpdate,
    ): CancelablePromise<src__modules__users__schemas__public__user__UserRead> {
        return __request(OpenAPI, {
            method: 'PATCH',
            url: '/api/v1/public/users/me',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Получить Telegram профиль текущего пользователя
     * Получить связанный Telegram профиль текущего пользователя.
     * @returns src__modules__users__schemas__public__telegram__TelegramRead Successful Response
     * @throws ApiError
     */
    public static getMyTelegramApiV1PublicUsersMeTelegramGet(): CancelablePromise<src__modules__users__schemas__public__telegram__TelegramRead> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/public/users/me/telegram',
        });
    }
}
