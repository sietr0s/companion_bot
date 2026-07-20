/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Чтение настроек Telegram-аккаунта (internal).
 */
export type src__modules__telegram_clients__schemas__internal__settings__TelegramSettingsRead = {
    id: string;
    account_id: string;
    use_whitelist: boolean;
    whitelist_chat_ids: Array<(string | number)>;
    created_at: string;
    updated_at: string;
};

