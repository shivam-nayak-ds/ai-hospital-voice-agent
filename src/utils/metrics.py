import time
import functools
from src.utils.logger import custom_logger as logger

def track_latency(component_name: str):
    """
    🔥 0.1% ELITE TOOL: Decorator to track execution time of any function.
    Useful for sub-1s optimization.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.perf_counter()
            result = func(*args, **kwargs)
            end_time = time.perf_counter()
            latency = (end_time - start_time) * 1000
            
            if latency > 500:
                logger.warning(f"⚠️  [LATENCY] {component_name} took {latency:.2f}ms (Slow!)")
            else:
                logger.info(f"⚡ [LATENCY] {component_name} took {latency:.2f}ms")
            
            return result
        return wrapper
    return decorator

class AshaMetrics:
    def __init__(self):
        self.stats = {
            "total_interactions": 0,
            "avg_stt_latency": 0,
            "avg_llm_latency": 0,
            "avg_tts_latency": 0
        }
    
    def log_interaction(self, stt_l, llm_l, tts_l):
        self.stats["total_interactions"] += 1
        # Moving average calculation
        n = self.stats["total_interactions"]
        self.stats["avg_stt_latency"] = (self.stats["avg_stt_latency"] * (n-1) + stt_l) / n
        self.stats["avg_llm_latency"] = (self.stats["avg_llm_latency"] * (n-1) + llm_l) / n
        self.stats["avg_tts_latency"] = (self.stats["avg_tts_latency"] * (n-1) + tts_l) / n
        
        logger.debug(f"📊 SYSTEM HEALTH: STT: {self.stats['avg_stt_latency']:.0f}ms | LLM: {self.stats['avg_llm_latency']:.0f}ms | TTS: {self.stats['avg_tts_latency']:.0f}ms")

metrics = AshaMetrics()
