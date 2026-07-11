/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ChangePasswordRequest } from '../models/ChangePasswordRequest';
import type { LoginRequest } from '../models/LoginRequest';
import type { RegisterRequest } from '../models/RegisterRequest';
import type { TokenResponse } from '../models/TokenResponse';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class AuthService {
    /**
     * Регистрация нового пользователя
     * Регистрация: создаёт учётную запись авторизации и возвращает JWT.
     *
     * Профиль пользователя создаётся отдельным запросом POST /users/.
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
     * Авторизация: проверяет email/пароль и возвращает JWT-токен.
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
     * Смена пароля
     * Сменить пароль текущего пользователя.
     * @param requestBody
     * @returns void
     * @throws ApiError
     */
    public static changePasswordApiV1PublicAuthMePasswordPatch(
        requestBody: ChangePasswordRequest,
    ): CancelablePromise<void> {
        return __request(OpenAPI, {
            method: 'PATCH',
            url: '/api/v1/public/auth/me/password',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Удаление учётной записи
     * Удалить учётную запись текущего пользователя (каскадное удаление профиля).
     *
     * Без пароля — удаление по JWT (auth_id).
     * @returns void
     * @throws ApiError
     */
    public static deleteAccountApiV1PublicAuthMeDelete(): CancelablePromise<void> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/api/v1/public/auth/me',
        });
    }
}
