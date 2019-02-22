# 检查 Istio 中 VirtualService 的引用完整性

一个小脚本，提供一个 VirtualService 的名称，会根据其中的 `destination`、`host`、`subset` 等元素，检查相关的 `DestinationRule`、`Service`、`Pod` 等资源。

~~~plain
./virtual-service-scanner.py flaskapp-default-v2
Validating VirtualService: flaskapp-default-v2
Destinations referenced: {'flaskapp.default.svc.cluster.local': ['v2', 'v3']}
Fetching all destination rules in current namespace.
Validating subsets of host flaskapp.default.svc.cluster.local
Service label is: {'app': 'flaskapp'}
Subset label is: {'version': 'v2'}
Pod selector: app=flaskapp,version=v2
1 pods found
Traceback (most recent call last):
  File "./virtual-service-scanner.py", line 148, in <module>
    main()
  File "./virtual-service-scanner.py", line 88, in main
    verify_virtualservice(args.object_name, kubectl_command)
  File "./virtual-service-scanner.py", line 117, in verify_virtualservice
    "Subset {} isn't defined.".format(subset_name)
AssertionError: Subset v3 isn't defined.
~~~


`virtual-service-scanner.py [VirtualService]`

会根据其中引用的 `host`、`subset` 对其依赖的 `DestinationRule`、`Service` 以及 `Pod` 进行逐一检查，如果其中有环节无法通过，脚本会出错退出，例如上面的例子中，`VirtualService` 引用了不存在的 `subset`： `v3`。