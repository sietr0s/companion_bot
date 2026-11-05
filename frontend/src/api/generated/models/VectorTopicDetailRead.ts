/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { MemoryMessageRead } from './MemoryMessageRead';
export type VectorTopicDetailRead = {
    id: string;
    conversation_id: string;
    title: string;
    seq_from: number;
    seq_to: number;
    message_count: number;
    kind?: string;
    partial?: boolean;
    created_at: string;
    messages?: Array<MemoryMessageRead>;
};

