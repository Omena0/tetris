from numpy import mean

fps_list = []
def calculate_fps(fps,iterations):
    fps_list.append(fps)

    if len(fps_list) > iterations:
        fps_list.pop(0)

    average = round(mean(fps_list), 2)

    return average

