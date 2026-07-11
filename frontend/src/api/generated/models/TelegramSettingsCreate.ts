/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Создание настроек Telegram-аккаунта (internal).
 */
export type TelegramSettingsCreate = {
    read_groups?: boolean;
    read_personal?: boolean;
    read_channels?: boolean;
    whitelist_chat_ids?: Array<(string | number)>;
};

