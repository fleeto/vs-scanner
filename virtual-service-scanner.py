#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import subprocess
import json


def command_wrapper(command):
    try:
        output = subprocess.check_output(command)
        return output.decode("utf-8")
    except subprocess.CalledProcessError:
        return None


def fetch_destination_rules(kube_command):
    output = command_wrapper(kube_command + ["get",
                                             "destinationrule",
                                             "-o", "json"])
    obj = json.loads(output)
    return obj["items"]


def host_subset_to_label(destination_rule_list, host, subset):
    for item in destination_rule_list:
        spec = item["spec"]
        if spec["host"] == host:
            subset_list = spec["subsets"]
            if subset == "":
                return subset_list
            for subset_item in subset_list:
                if subset == subset_item["name"]:
                    return subset_item["labels"]
    return None


def get_service_label_map(host):
    service_name = host
    namespace = ""
    cmd = ["kubectl", "get", "svc", service_name,
           "-o", "json"]
    if "." in host:
        seg = host.split(".")
        if seg[2] == "svc":
            service_name = seg[0]
            cmd = ["kubectl", "get", "svc",
                   service_name, "-n", seg[1],
                   "-o", "json"]
            namespace = seg[1]
        else:
            return None, ""
    output = command_wrapper(cmd)
    obj = json.loads(output)
    return obj["spec"]["selector"], namespace


def build_target_list(virtual_service):
    target_list = {}
    for key, value in virtual_service["spec"].items():
        if key in ["tcp", "tls", "http"]:
            for match in value:
                for route in match["route"]:
                    destination = route["destination"]
                    host = destination["host"]
                    if "subset" in destination.keys():
                        subset = destination["subset"]
                    if host in target_list.keys():
                        target_list[host].append(subset)
                    else:
                        target_list[host] = [subset]
    return target_list


def main():
    parser = argparse.ArgumentParser(description='A simple script to validate VirtualService of istio.')
    parser.add_argument("object_name",
                        help="VirtualService name to be validated")

    parser.add_argument("-k", "--kubectl-config", default="")
    args = parser.parse_args()
    kubectl_command = ['kubectl']
    if args.kubectl_config != "":
        kubectl_command += args.kubectl_config.split(" ")
    verify_virtualservice(args.object_name, kubectl_command)


def verify_virtualservice(virtualservice_name, kube_command):
    # spec{"tcp/http"}[match]{"route"}{"destination"}
    print(
        "Validating VirtualService: {}".format(virtualservice_name))
    command = kube_command + ["get", "virtualservice",
                              virtualservice_name, "-o", "json"]
    output = command_wrapper(command)
    obj = json.loads(output)

    target_list = build_target_list(obj)
    print("Destinations referenced: {}".format(str(target_list)))
    print("Fetching all destination rules in current namespace.")
    destinationrule_list = fetch_destination_rules(kube_command)
    for virtualservice_host, virtualservice_subset_list in target_list.items():
        print("Validating subsets of host {}".format(virtualservice_host))
        service_label_map, service_namespace = \
            get_service_label_map(virtualservice_host)
        assert service_label_map is not None, \
            "Host name '{}' isn't supported.".format(virtualservice_host)
        print(
            "Service label is: {}".format(str(service_label_map)))

        for subset_name in virtualservice_subset_list:
            subset_label_map = host_subset_to_label(
                destinationrule_list, virtualservice_host, subset_name)
            assert subset_label_map is not None, \
                "Subset {} isn't defined.".format(subset_name)
            print(
                "Subset label is: {}".format(str(subset_label_map)))
            pod_label_map = service_label_map.copy()
            for key, value in subset_label_map.items():
                if key in pod_label_map.keys():
                    assert pod_label_map[key] == value, \
                        "Label {} conflict: in service: {} in subset: {}".format(
                            key, pod_label_map[key], value)
                else:
                    pod_label_map[key] = value

            # selector -> parameter
            selector = ",".join(
                ["{}={}".format(key, value) for key, value in pod_label_map.items()])
            print("Pod selector: {}".format(selector))
            command = ["kubectl", "get", "po", "-l", selector,
                       "-o", "json"]
            if len(service_namespace) > 0:
                command += ["-n", service_namespace]

            pod_list = json.loads(command_wrapper(command))["items"]
            assert len(pod_list) > 0, "No pod found"
            print("{} pods found".format(len(pod_list)))




if __name__ == "__main__":
    main()
