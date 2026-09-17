#!/usr/bin/env python3
"""
Streaming mutation ext_proc server
Purpose: Validate that ext_proc can mutate streaming content
without breaking the stream.

Simple mutation: foo → ***
"""

import asyncio
import logging
from concurrent import futures
import grpc
from envoy.service.ext_proc.v3 import external_processor_pb2, external_processor_pb2_grpc

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)


class StreamingMutationService(external_processor_pb2_grpc.ExternalProcessorServicer):
    """
    Minimal ext_proc service for streaming mutation validation.
    Mutates chunks: foo → ***
    """

    async def Process(self, request_iterator, context):
        """
        Bidirectional streaming RPC for ext_proc
        """
        chunk_count = 0
        total_bytes = 0
        total_mutated = 0

        async for request in request_iterator:
            chunk_count += 1

            if request.HasField('response_headers'):
                logger.info(f"[{chunk_count}] Response headers received")
                yield external_processor_pb2.ProcessingResponse()

            elif request.HasField('response_body'):
                body_msg = request.response_body
                original_body = body_msg.body
                chunk_size = len(original_body)
                total_bytes += chunk_size
                end_of_stream = body_msg.end_of_stream

                # Try to decode and check content
                try:
                    text = original_body.decode('utf-8')
                except:
                    text = "(binary)"

                # Simple mutation: foo → ***
                mutated_body = original_body
                if b'foo' in original_body:
                    mutated_body = original_body.replace(b'foo', b'***')
                    total_mutated += 1
                    logger.info(
                        f"[{chunk_count}] MUTATED: '{text.strip()}' → '{mutated_body.decode('utf-8', errors='replace').strip()}' "
                        f"(end_of_stream={end_of_stream})"
                    )
                else:
                    logger.info(
                        f"[{chunk_count}] PASSTHROUGH: '{text.strip()}' "
                        f"(end_of_stream={end_of_stream})"
                    )

                # Return mutated body
                if mutated_body != original_body:
                    yield external_processor_pb2.ProcessingResponse(
                        body_mutation=external_processor_pb2.BodyMutation(
                            body=mutated_body
                        )
                    )
                else:
                    yield external_processor_pb2.ProcessingResponse()

            else:
                yield external_processor_pb2.ProcessingResponse()

        logger.info(
            f"Stream complete: {chunk_count} chunks, {total_bytes}B total, {total_mutated} mutated"
        )


async def serve():
    """Start gRPC server"""
    server = grpc.aio.server(futures.ThreadPoolExecutor(max_workers=10))
    external_processor_pb2_grpc.add_ExternalProcessorServicer_to_server(
        StreamingMutationService(),
        server
    )
    server.add_insecure_port('[::]:9000')
    await server.start()
    logger.info("✓ Streaming mutation ext_proc started on port 9000")
    logger.info("  Mode: FULL_DUPLEX_STREAMED")
    logger.info("  Action: Mutate 'foo' → '***', pass through others")
    await server.wait_for_termination()


if __name__ == '__main__':
    asyncio.run(serve())
