# Final Review Transcript

## segment_006_block_0017 - core_concept
Time: 196.04–207.3
Why included: Policy repair kept concise block block_0017.

One solution is to put a little piece of RAM right on the CPU -- called a cache. There isn’t a lot of space on a processor’s chip, so most caches are just kilobytes or maybe megabytes in size, where RAM is usually gigabytes.

## segment_006_block_0018 - core_concept
Time: 207.3–216.569
Why included: Policy repair kept concise block block_0018.

Having a cache speeds things up in a clever way. When the CPU requests a memory location from RAM, the RAM can transmit not just one single value, but a whole block of data.

## segment_006_block_0019 - core_concept
Time: 216.569–225.92
Why included: Policy repair kept concise block block_0019.

This takes only a little bit more time than transmitting a single value, but it allows this data block to be saved into the cache. This tends to be really useful because computer data is often arranged and processed sequentially.

## segment_006_block_0020 - core_concept
Time: 225.92–234.2
Why included: Policy repair kept concise block block_0020.

For example, let say the processor is totalling up daily sales for a restaurant. It starts by fetching the first transaction from RAM at memory location 100.

## segment_006_block_0023 - core_concept
Time: 254.73–264.99
Why included: Policy repair kept concise block block_0023.

Because the cache is so close to the processor, it can typically provide the data in a single clock cycle -- no waiting required. This speeds things up tremendously over having to go back and forth to RAM every single time.

## segment_006_block_0024 - core_concept
Time: 264.99–274.09
Why included: Policy repair kept concise block block_0024.

When data requested in RAM is already stored in the cache like this it’s called a cache hit, and if the data requested isn’t in the cache, so you have to go to RAM, it’s a called a cache miss.
