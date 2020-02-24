// Generated using py-ts-interfaces.  See https://github.com/cs-cordero/py-ts-interfaces

interface TaskData {
    name: string;
    progress_supported: boolean;
    progress: number;
    string_rep: string;
    return_code: number;
}

interface TaskQueueData {
    maxqueue: number;
    paused: boolean;
    queue: Array<TaskData>;
    completed: Array<string>;
}

interface HddData {
    serial: string;
    model: string;
    wwn: string;
    capacity: number;
    health_status: string;
    task_queue: TaskQueueData;
}