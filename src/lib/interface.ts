// Generated using py-ts-interfaces.
// See https://github.com/cs-cordero/py-ts-interfaces

interface Attribute {
    number: number;
    flags: number;
    raw_value: number;
    threshold: number;
    attr_type: string;
    updated_freq: string;
    value: number;
    when_failed: string;
    worst: number;
}

interface Smart {
    last_captured: string;
    attributes: Array<Attribute>;
    firmware: string;
    interface: string;
    messages: Array<string>;
    smart_capable: boolean;
    smart_enabled: boolean;
    assessment: string;
    test_capabilities: Array<[string, boolean]>;
}

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
    current_task: TaskData;
}

interface HddData {
    serial: string;
    model: string;
    wwn: string;
    capacity: number;
    status: string;
    assessment: string;
    task_queue: TaskQueueData;
    node: string;
    port: string;
    smart: Smart;
}