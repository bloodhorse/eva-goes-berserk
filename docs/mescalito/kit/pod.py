"""One rented card for a mescalito night: the full llama.cpp image (converter, quantize,
llama-completion), a disk big enough for both models' weights, and sshd installed by the
start command so the mac can scp the kit up and the pages down. Modelled on olmo-dreamer's
pod.py; the traps it carries are the same (bash -c loses the image's library path, cloudflare
403s python's default user-agent, the key comes from the keychain at the point of use).

    python3 pod.py create              # prints the pod id; sshd takes ~1 min after RUNNING
    python3 pod.py get <id>            # status, cost, public ip and the 22 -> host port map
    python3 pod.py ssh <id>            # prints the ssh line (host, port, key) once the port is mapped
    python3 pod.py kill <id>           # terminate — the only thing that stops the bill

The public key is not a secret and rides in the pod's env: the start command appends it to
root's authorized_keys. RunPod's own images do this from the account's key; ghcr's don't."""

import json, os, subprocess, sys, urllib.request, urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
PUBKEY = os.path.expanduser("~/.ssh/id_ed25519_vast.pub")
BOOT = ("export DEBIAN_FRONTEND=noninteractive; apt-get update -qq && apt-get install -y -qq openssh-server >/dev/null"
        " && mkdir -p /run/sshd ~/.ssh && chmod 700 ~/.ssh && echo \"$PUBLIC_KEY\" >> ~/.ssh/authorized_keys"
        " && chmod 600 ~/.ssh/authorized_keys && /usr/sbin/sshd -D -e")


def key():
    return subprocess.run(["security", "find-generic-password", "-a", os.environ["USER"],
                           "-s", "RUNPOD_API_KEY", "-w"], capture_output=True, text=True).stdout.strip()


def call(path, body=None, method=None):
    r = urllib.request.Request("https://rest.runpod.io/v1" + path,
                               data=json.dumps(body).encode() if body is not None else None,
                               method=method or ("POST" if body is not None else "GET"))
    r.add_header("Authorization", f"Bearer {key()}")
    r.add_header("Content-Type", "application/json")
    r.add_header("User-Agent", "curl/8.7.1")
    try:
        with urllib.request.urlopen(r, timeout=60) as resp:
            raw = resp.read()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raise SystemExit(f"runpod {e.code} on {path}: {e.read()[:400].decode('utf-8', 'replace')}") from None


def sshport(p):
    for m in p.get("portMappings") or []:
        if isinstance(m, dict) and str(m.get("privatePort")) == "22":
            return m.get("publicPort")
    pm = p.get("portMappings")
    if isinstance(pm, dict):
        return pm.get("22")
    return None


if sys.argv[1] == "create":
    pod = call("/pods", {
        "name": "mescalito",
        "imageName": "ghcr.io/ggml-org/llama.cpp:full-cuda",
        "cloudType": "SECURE",
        "computeType": "GPU",
        "gpuTypeIds": ["NVIDIA A40", "NVIDIA RTX A6000"],       # 48 GB: olmo's first twenty layers in bf16 need it
        "gpuTypePriority": "availability",
        "gpuCount": 1,
        "containerDiskInGb": 150,       # nemo hf 25 + bf16 gguf 25 (deleted after quant) + q4 8 + olmo hf 64 + olmo q4 18
        "volumeInGb": 0,
        "ports": ["22/tcp"],
        "supportPublicIp": True,
        "env": {"PUBLIC_KEY": open(PUBKEY).read().strip()},
        "dockerEntrypoint": ["bash", "-c"],
        "dockerStartCmd": [BOOT],
        "allowedCudaVersions": ["12.8", "12.9", "13.0"],
    })
    print(json.dumps({k: pod.get(k) for k in ("id", "name", "machine", "desiredStatus", "costPerHr",
                                              "gpu", "image")}, indent=1, default=str))
elif sys.argv[1] == "get":
    p = call(f"/pods/{sys.argv[2]}")
    print(json.dumps({k: p.get(k) for k in ("id", "desiredStatus", "costPerHr", "machine", "publicIp",
                                            "portMappings", "lastStatusChange")}, indent=1, default=str))
elif sys.argv[1] == "ssh":
    p = call(f"/pods/{sys.argv[2]}")
    port = sshport(p)
    if not p.get("publicIp") or not port:
        raise SystemExit(f"no ssh yet: status {p.get('desiredStatus')}, ip {p.get('publicIp')}, ports {p.get('portMappings')}")
    print(f"ssh -i {PUBKEY[:-4]} -p {port} -o StrictHostKeyChecking=accept-new root@{p['publicIp']}")
elif sys.argv[1] == "kill":
    call(f"/pods/{sys.argv[2]}", method="DELETE")
    print("terminated", sys.argv[2])
