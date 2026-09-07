"""Generic visual guidance, not project geometry or test evidence.

Run: pip install matplotlib; python render_figure_style_guide.py
Font: install Noto Sans CJK SC or Microsoft YaHei for Chinese labels.
"""
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

plt.rcParams['font.sans-serif']=['Microsoft YaHei','Noto Sans CJK SC','DejaVu Sans']
plt.rcParams['axes.unicode_minus']=False
fig=plt.figure(figsize=(12,5.8),dpi=150,facecolor='#FAF9F5')
fig.text(.05,.9,'技术图：克制用色，几何关系清楚',fontsize=22,weight='bold',color='#30332F')
fig.text(.05,.835,'通用规则示意 · 不含项目数据或性能结论',fontsize=12,color='#646962')
left=fig.add_axes([.05,.17,.43,.57]);left.axis('off')
left.text(0,.93,'01  黑白为主，棕色只作局部区分',fontsize=14,weight='bold')
for y,label,detail in [(.57,'输入','已知来源 / 单位 / 条件'),(.31,'处理','机制与接口，不用大色块填充'),(.05,'输出','结果与限制分别说明')]:
    left.add_patch(Rectangle((0,y),1,.2,facecolor='white',edgecolor='#C4C6BF',lw=1))
    left.add_patch(Rectangle((0,y),.17,.2,facecolor='#EBE3D5',edgecolor='none'))
    left.text(.085,y+.1,label,fontsize=13,ha='center',va='center',color='#604932')
    left.text(.21,y+.1,detail,fontsize=12,va='center',color='#30332F')
    if y>.1:left.annotate('',(.49,y-.05),(.49,y),arrowprops={'arrowstyle':'->','color':'#555A51'})
right=fig.add_axes([.56,.21,.29,.47]);right.set_facecolor('white');right.set_xlim(0,10);right.set_ylim(0,8);right.set_aspect('equal')
right.set_xticks(range(11));right.set_yticks(range(9));right.grid(color='#DDE1D7',lw=.55);right.set_xticklabels([]);right.set_yticklabels([]);right.tick_params(length=0)
for x,y,w,h in [(1,4,2,3),(7,1,2,2)]:
    right.add_patch(Rectangle((x-.4,y-.4),w+.8,h+.8,facecolor='#EBE3D5',edgecolor='#9B805E',linestyle='--',lw=.9,clip_on=True,zorder=2))
    right.add_patch(Rectangle((x,y),w,h,facecolor='white',edgecolor='#41493E',lw=1.2,zorder=3))
    right.text(x+w/2,y+h/2,'禁区',ha='center',va='center',fontsize=11,zorder=4)
right.plot([.7,3.8,5,6.4,9],[.8,2,3.7,4.2,6.8],color='#755B3D',lw=2,zorder=4)
fig.text(.56,.7,'02  绘图区与说明区分开',fontsize=14,weight='bold')
fig.text(.87,.58,'白色：禁区\n\n虚线：裕量\n\n棕线：示意',fontsize=11,color='#535E51')
fig.text(.05,.075,'正文与表格继承模板  /  少量必要彩照保留原色  /  装饰不改变数据与物理关系',fontsize=12,color='#646962')
fig.savefig(Path(__file__).with_name('figure-style-guide.png'),facecolor=fig.get_facecolor())
plt.close(fig)
