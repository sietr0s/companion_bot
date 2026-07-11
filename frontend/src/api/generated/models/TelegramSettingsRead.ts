/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Чтение настроек Telegram-аккаунта (internal).
 */
export type TelegramSettingsRead = {
    id: string;
    account_id: string;
    read_groups: boolean;
    read_personal: boolean;
    read_channels: boolean;
    whitelist_chat_ids: Array<(string | number)>;
    created_at: string;
    updated_at: string;
};

