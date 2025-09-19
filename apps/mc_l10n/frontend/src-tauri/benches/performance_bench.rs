use criterion::{black_box, criterion_group, criterion_main, Criterion, BenchmarkId};
use std::time::Duration;

// 模拟的性能测试函数
fn fibonacci(n: u64) -> u64 {
    match n {
        0 => 1,
        1 => 1,
        n => fibonacci(n-1) + fibonacci(n-2),
    }
}

fn string_processing(input: &str) -> String {
    input
        .chars()
        .filter(|c| c.is_alphabetic())
        .map(|c| c.to_uppercase().collect::<String>())
        .collect::<Vec<String>>()
        .join("")
}

fn vector_operations(size: usize) -> Vec<i32> {
    let mut vec = Vec::with_capacity(size);
    for i in 0..size {
        vec.push(i as i32);
    }
    
    vec.iter()
        .filter(|&&x| x % 2 == 0)
        .map(|&x| x * 2)
        .collect()
}

// 基准测试函数
fn criterion_benchmark(c: &mut Criterion) {
    // Fibonacci 基准测试
    let mut group = c.benchmark_group("fibonacci");
    for i in [20u64, 25, 30].iter() {
        group.bench_with_input(BenchmarkId::new("recursive", i), i, |b, i| {
            b.iter(|| fibonacci(black_box(*i)))
        });
    }
    group.finish();

    // 字符串处理基准测试
    let mut group = c.benchmark_group("string_processing");
    let test_strings = vec![
        "Hello, World!",
        "The quick brown fox jumps over the lazy dog",
        "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.",
    ];
    
    for (i, input) in test_strings.iter().enumerate() {
        group.bench_with_input(
            BenchmarkId::new("uppercase_filter", i),
            input,
            |b, input| {
                b.iter(|| string_processing(black_box(input)))
            },
        );
    }
    group.finish();

    // 向量操作基准测试
    let mut group = c.benchmark_group("vector_operations");
    for size in [100, 1000, 10000].iter() {
        group.bench_with_input(
            BenchmarkId::new("filter_map", size),
            size,
            |b, size| {
                b.iter(|| vector_operations(black_box(*size)))
            },
        );
    }
    group.finish();

    // 内存分配基准测试
    c.bench_function("memory_allocation", |b| {
        b.iter(|| {
            let _vec: Vec<u64> = (0..1000).collect();
        })
    });

    // JSON 序列化/反序列化基准测试
    #[derive(serde::Serialize, serde::Deserialize)]
    struct TestData {
        id: u32,
        name: String,
        values: Vec<f64>,
    }

    let test_data = TestData {
        id: 123,
        name: "Test Data".to_string(),
        values: (0..100).map(|i| i as f64 * 0.1).collect(),
    };

    c.bench_function("json_serialize", |b| {
        b.iter(|| {
            serde_json::to_string(&test_data).unwrap()
        })
    });

    let json_string = serde_json::to_string(&test_data).unwrap();
    c.bench_function("json_deserialize", |b| {
        b.iter(|| {
            let _: TestData = serde_json::from_str(black_box(&json_string)).unwrap();
        })
    });
}

criterion_group!(benches, criterion_benchmark);
criterion_main!(benches);