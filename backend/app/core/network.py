"""请求网络信息解析工具。"""

from ipaddress import ip_address, ip_network

from fastapi import Request

from .config import settings


def _is_trusted_proxy(address: str) -> bool:
    """仅当直接连接方属于显式配置的代理网段时才信任转发头。"""
    try:
        client_address = ip_address(address)
    except ValueError:
        return False
    for network in settings.trusted_proxy_networks:
        try:
            if client_address in ip_network(network, strict=False):
                return True
        except ValueError:
            # 单个错误配置不能让请求日志中间件失效。
            continue
    return False


def get_client_ip(request: Request) -> str:
    """解析真实客户端 IP，未配置可信代理时忽略 X-Forwarded-For。"""
    direct_address = request.client.host if request.client is not None else "unknown"
    forwarded = request.headers.get("x-forwarded-for")
    if not forwarded or not _is_trusted_proxy(direct_address):
        return direct_address

    addresses = [part.strip() for part in forwarded.split(",") if part.strip()]
    # 从代理链右侧开始剥离可信代理，取第一个不在可信网段的地址。
    for address in reversed(addresses):
        if not _is_trusted_proxy(address):
            try:
                ip_address(address)
            except ValueError:
                continue
            return address
    return direct_address
