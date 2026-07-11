/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { MediaItem } from './MediaItem';
/**
 * Схема чтения сообщения из Telegram API.
 */
export type MessageRead = {
    id: number;
    chat_id: number;
    sender_id?: (number | null);
    text?: (string | null);
    media?: Array<MediaItem>;
    date: string;
};

