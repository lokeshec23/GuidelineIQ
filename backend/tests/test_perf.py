import asyncio
import time

async def dummy_cpu_bound_task():
    # Simulate a 1 second blocking task
    time.sleep(1)
    
async def test_to_thread():
    heartbeats = []
    
    async def heartbeat():
        for _ in range(15):
            heartbeats.append(time.time())
            await asyncio.sleep(0.1)
            
    # test 1: direct call (blocks event loop)
    heartbeats.clear()
    task = asyncio.create_task(heartbeat())
    await dummy_cpu_bound_task()
    await asyncio.sleep(0.6) # allow heartbeats to finish
    await task 
    
    # check gap > 0.5s for direct call
    gaps = [heartbeats[i] - heartbeats[i-1] for i in range(1, len(heartbeats))]
    max_gap_direct = max(gaps) if gaps else 0
    print(f'Max gap when BLOCKING: {max_gap_direct:.2f}s')

    # test 2: to_thread call (non-blocking)
    heartbeats.clear()
    task = asyncio.create_task(heartbeat())
    await asyncio.to_thread(time.sleep, 1)
    await asyncio.sleep(0.6)
    await task 
    
    gaps = [heartbeats[i] - heartbeats[i-1] for i in range(1, len(heartbeats))]
    max_gap_thread = max(gaps) if gaps else 0
    # Write results to file
    with open('tests/test_results.txt', 'w') as f:
        f.write(f'Max gap when BLOCKING: {max_gap_direct:.2f}s\n')
        f.write(f'Max gap when USING asyncio.to_thread: {max_gap_thread:.2f}s\n')
        
        if max_gap_thread < 0.2 and max_gap_direct > 0.9:
            f.write('SUCCESS: asyncio.to_thread prevents event loop blocking!\n')
        else:
            f.write('FAILURE: asyncio.to_thread did not behave as expected.\n')

if __name__ == '__main__':
    asyncio.run(test_to_thread())
