import json
from urllib.request import Request, urlopen


# 修改为你们自己的参赛队号
BASE_URL = "http://127.0.0.1:2026"
ROBOT_ID = "<参赛队号>"


def post(path, payload):
    request = Request(
        BASE_URL + path,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=5) as http_response:
        response = json.loads(http_response.read().decode("utf-8"))
    print(path, response)
    return response


def base(request_id):
    return {
        "arena_id": "default",
        "robot_id": ROBOT_ID,
        "request_id": request_id,
    }


def action(request_id, x, y, channel):
    payload = base(request_id)
    payload["position"] = {"x": x, "y": y}
    payload["channel"] = channel
    return payload


def main():
    enter_response = post("/enter", base("enter-1"))
    if enter_response.get("accepted") is not True:
        print("进入失败")
        return

    remaining_time = enter_response["remaining_real_duration_s"]
    print("本局可用现实时间：", remaining_time, "秒")

    # 与第10节计时示例完全相同的四个动作。
    actions = [
        ("/measure", action("measure-1", 300, 400, 1)),
        ("/measure", action("measure-2", 300, 400, 2)),
        ("/clear", action("clear-1", 300, 0, 3)),
        ("/measure", action("measure-3", 300, 0, 2)),
    ]

    for path, payload in actions:
        # 如果因网络故障重试本动作，必须复用这个payload及其中的request_id。
        response = post(path, payload)
        if response.get("accepted") is not True:
            print("请求未执行")
            return

        if path == "/measure":
            if response["measure_result"] == "direction":
                print("示向度：", response["svd_deg"], "度")
            elif response["measure_result"] == "near":
                print("距离过近，没有示向度")
            else:
                print("未测得信号")
        else:
            if response["clear_result"] == "success":
                print("清除成功")
            else:
                print("清除位置附近没有目标")

    exit_response = post("/exit", base("exit-1"))
    if exit_response.get("accepted") is True:
        print("退出原因：", exit_response["exit_reason"])

main()
