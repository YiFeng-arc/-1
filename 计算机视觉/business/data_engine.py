import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator, AutoMinorLocator
from scipy.interpolate import griddata

plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial']  # 支持中文显示
plt.rcParams['axes.unicode_minus'] = False

class FieldAnalyzer:
    """
    电场数值分析引擎：采用SciPy高次样条插值，重构等势面及电场梯度场，并渲染图表。
    """
    def __init__(self):
        self.points_x = []
        self.points_y = []
        self.voltages = []

    def add_data_point(self, x, y, voltage):
        """记录每一次触发成功的数据锚点"""
        self.points_x.append(x)
        self.points_y.append(y)
        self.voltages.append(voltage)
        print(f"[数据内核] 接收入库: 物理坐标 X={x:.1f}mm, Y={y:.1f}mm, 检测电压={voltage}V, 当前总点数={len(self.points_x)}")

    def clear_data(self):
        self.points_x = []
        self.points_y = []
        self.voltages = []

    def generate_electric_field_map(self, use_ai_interpolation=False):
        """
        利用收集到的散点数据，生成连续二维平面的等势线与电场线。
        如果 use_ai_interpolation 为真，则进行稠密网格空间插值以补全全画幅未知点细节。
        否则默认贴合学生手绘记录习惯，采用直接数据点迹连线的Delaunay三角网拓扑绘制等势面。
        """
        if len(self.points_x) < 5:
            return

        print(f"\n[推演机制] 开始生成场型图, AI全场插值补偿={use_ai_interpolation}")
        
        fig, ax = plt.subplots(figsize=(10, 8), dpi=120)
        ax.set_facecolor('#FFFFFF') # 回归白底以更接近学术教材参考图
        ax.grid(True, linestyle=':', color='#A0A0A0', alpha=0.7)

        pts_x = np.array(self.points_x)
        pts_y = np.array(self.points_y)
        vals = np.array(self.voltages)
        
        # 定义等势线彩色阶梯（对应问题：1V 2V 3V 不同颜色）
        v_min, v_max = np.floor(np.nanmin(vals)), np.ceil(np.nanmax(vals))
        levels = np.arange(v_min, v_max + 0.5, 0.5)

        # 构建稠密绘图网格以生成平滑曲线，即使点数较少也能覆盖全场
        grid_x, grid_y = np.mgrid[-100:100:150j, -100:100:150j]

        if use_ai_interpolation:
            # AI补偿模式：采用物理特性相符的径向基函数(RBF)插值运算，支持全局曲面光滑外推
            from scipy.interpolate import Rbf
            try:
                # epsilon控制平滑度，thin_plate对于多点或者拉普拉斯形变较好，
                # 但 multiquadric 表现类似电场 1/r 势能场的自然分布
                rbf_interp = Rbf(pts_x, pts_y, vals, function='multiquadric', smooth=0.1)
                grid_z = rbf_interp(grid_x, grid_y)
            except Exception as e:
                print(f"[RBF降级] RBF生成失败 {e}，回退至基础网格插值")
                grid_z = griddata((pts_x, pts_y), vals, (grid_x, grid_y), method='cubic')
            
            # 绘制全场平滑等势线
            contour_lines = ax.contour(grid_x, grid_y, grid_z, levels=levels, cmap='jet', linewidths=2.0, zorder=3)
            ax.clabel(contour_lines, inline=True, fontsize=11, fmt='%1.1fV')

            # 绘制电场线背景 (平滑连贯的电场梯度)
            Ey, Ex = np.gradient(-grid_z)
            Ex, Ey = np.nan_to_num(Ex), np.nan_to_num(Ey)
            ax.streamplot(grid_x[:, 0], grid_y[0, :], Ex.T, Ey.T, 
                         color='cornflowerblue', linewidth=1.0, density=1.2, arrowsize=1.5, zorder=2)
        else:
            # 传统学生测绘模拟：采用二次/三次多项式插值的平滑曲线，取代生硬的直线连线
            try:
                # 默认情况下由于学生点较少，用 griddata 的 cubic 进行平滑拟合，实现“合适的曲线分布图”
                grid_z = griddata((pts_x, pts_y), vals, (grid_x, grid_y), method='cubic')
                # 补全 NaN（由不在凸包内部引起）
                if np.isnan(grid_z).any():
                    grid_z_lin = griddata((pts_x, pts_y), vals, (grid_x, grid_y), method='nearest')
                    grid_z[np.isnan(grid_z)] = grid_z_lin[np.isnan(grid_z)]
                
                contour_lines = ax.contour(grid_x, grid_y, grid_z, levels=levels, cmap='jet', linewidths=2.0, zorder=3)
                ax.clabel(contour_lines, inline=True, fontsize=11, fmt='%1.1fV')
                
                Ey, Ex = np.gradient(-grid_z)
                Ex, Ey = np.nan_to_num(Ex), np.nan_to_num(Ey)
                ax.streamplot(grid_x[:, 0], grid_y[0, :], Ex.T, Ey.T, 
                             color='cornflowerblue', linewidth=0.8, density=0.8, arrowsize=1.5, zorder=1)
            except Exception as e:
                print(f"[插值警告] 数据点集无法有效平滑：{e}")

        # 无论何种模式，点都要画出来
        ax.scatter(pts_x, pts_y, c=vals, cmap='jet', marker='o', s=60, edgecolors='black', label='采集节点', zorder=5)

        # 完善图表文字说明
        ax.set_title('同轴圆柱形电缆电极横截面上的静电场分布', fontsize=16, fontweight='bold', pad=15)
        ax.set_xlabel('探针点位 X 轴向距离 (mm)', fontsize=12)
        ax.set_ylabel('探针点位 Y 轴向距离 (mm)', fontsize=12)
        ax.set_xlim(-85, 85)
        ax.set_ylim(-85, 85)

        # 直观的图例，帮助学生读图
        from matplotlib.lines import Line2D
        custom_lines = [
            Line2D([0], [0], color='red', lw=2.0, label='等势线 (多色彩标示)'),
            Line2D([0], [0], color='cornflowerblue', lw=1.2, label='电场线 (梯度正交)'),
            Line2D([0], [0], marker='o', color='w', markerfacecolor='orange', markeredgecolor='k', markersize=9, label='实际采样记录')
        ]
        ax.legend(handles=custom_lines, loc='upper right', framealpha=0.95, edgecolor='#DDDDDD')
        
        save_path = "electrostatic_field_result.png"
        plt.savefig(save_path, bbox_inches='tight')
        print(f"[数据内核] 直观标准的计算机绘图已输出至: {save_path}")
        plt.show()
