"""RabbitMQ message broker management."""
import json
import os
from typing import Callable, Optional

import pika


class RabbitMQBroker:
    """Manages RabbitMQ connections and message publishing."""

    def __init__(
        self,
        host: str | None = None,
        user: str | None = None,
        password: str | None = None,
        queue: str | None = None,
    ):
        """Initialize RabbitMQ broker.
        
        Args:
            host: RabbitMQ host. If None, reads from RABBITMQ_HOST env var.
            user: RabbitMQ user. If None, reads from RABBITMQ_USER env var.
            password: RabbitMQ password. If None, reads from RABBITMQ_PASSWORD env var.
            queue: Queue name. If None, reads from RABBITMQ_QUEUE env var.
        """
        self.host = host or os.getenv("RABBITMQ_HOST", "rabbitmq")
        self.user = user or os.getenv("RABBITMQ_USER", "app")
        self.password = password or os.getenv("RABBITMQ_PASSWORD", "app")
        self.queue = queue or os.getenv("RABBITMQ_QUEUE", "audio.jobs")

    def _get_channel(self) -> pika.adapters.blocking_connection.BlockingChannel:
        """Get a new RabbitMQ channel.
        
        Returns:
            A new RabbitMQ channel.
            
        Raises:
            pika.exceptions.Pika: If connection fails.
        """
        credentials = pika.PlainCredentials(self.user, self.password)
        params = pika.ConnectionParameters(host=self.host, credentials=credentials)
        connection = pika.BlockingConnection(params)
        channel = connection.channel()
        channel.queue_declare(queue=self.queue, durable=True)
        return channel

    def publish_message(self, message: dict) -> None:
        """Publish a message to the queue.
        
        Args:
            message: Message dictionary to publish.
            
        Raises:
            pika.exceptions.Pika: If publishing fails.
        """
        channel = self._get_channel()
        try:
            channel.basic_publish(
                exchange="",
                routing_key=self.queue,
                body=json.dumps(message),
                properties=pika.BasicProperties(
                    delivery_mode=pika.spec.PERSISTENT_DELIVERY_MODE
                ),
            )
        finally:
            channel.connection.close()

    def consume_messages(self, callback: Callable, prefetch_count: int = 1) -> None:
        """Start consuming messages from the queue.
        
        Args:
            callback: Callback function to process messages.
            prefetch_count: Number of messages to prefetch.
        """
        channel = self._get_channel()
        channel.basic_qos(prefetch_size=0, prefetch_count=prefetch_count, global_qos=False)
        channel.basic_consume(queue=self.queue, on_message_callback=callback)
        
        try:
            channel.start_consuming()
        except KeyboardInterrupt:
            channel.stop_consuming()
            channel.connection.close()

    def is_healthy(self) -> bool:
        """Check broker health.
        
        Returns:
            True if broker is accessible, False otherwise.
        """
        try:
            channel = self._get_channel()
            channel.connection.close()
            return True
        except Exception:
            return False
