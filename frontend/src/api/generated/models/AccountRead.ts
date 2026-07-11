/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Схема чтения Telegram-аккаунта.
 */
export type AccountRead = {
    id: string;
    auth_id: string;
    phone: string;
    is_connected: boolean;
    first_name?: (string | null);
    last_name?: (string | null);
    username?: (string | null);
    telegram_id?: (number | null);
    created_at: string;
    updated_at: string;
};

