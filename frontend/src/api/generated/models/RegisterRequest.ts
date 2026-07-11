/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Запрос на регистрацию нового пользователя.
 */
export type RegisterRequest = {
    identifier: string;
    identifier_type: 'email' | 'phone' | 'telegram';
    password: string;
};

