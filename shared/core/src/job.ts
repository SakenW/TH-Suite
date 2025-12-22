
export interface Job {
    id: string;
    status: 'pending' | 'running' | 'completed' | 'failed';
}
