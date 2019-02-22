# 检查 Istio 中 VirtualService 的引用完整性

一个小脚本，提供一个 VirtualService 的名称，会根据其中的 `destination`、`host`、`subset` 等元素，检查相关的 `DestinationRule`、`Service`、`Pod` 等资源。