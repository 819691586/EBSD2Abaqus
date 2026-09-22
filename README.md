# EBSD2Abaqus

将 Oxford CTF 格式的二维 EBSD 数据转换为可继续编辑的 Abaqus 基础模型。

项目只负责晶粒组织建模，不添加载荷、边界条件、分析步、缺口、裂纹、损伤或 XFEM 设置。生成的基础 CAE 可以复制后用于拉伸、疲劳或裂纹扩展等不同分析。

## 生成内容

- 每个 EBSD 像素对应一个二维有限元；
- 按 MTEX 重构结果建立晶粒单元集合；
- 为每个晶粒创建独立材料与截面；
- 将晶粒平均 Bunge Euler 角写入 `*User Material` 常数；
- 自动创建 `LEFT`、`RIGHT`、`BOTTOM`、`TOP` 和 `ALL_ELEMENTS` 集合；
- 输出晶粒表、晶粒编号图、IPF 预览、Abaqus INP 和 CAE。

## 环境要求

- Windows；
- MATLAB，并已安装和配置 MTEX；
- Python 3；
- Abaqus/CAE，且 `abaqus` 命令已加入系统环境。

## 使用方法

1. 将 Oxford CTF 文件命名为 `ebsd.ctf`，放入 `input` 文件夹。
2. 根据材料修改 `config.json` 中的相名称、晶体对称性、晶格常数和晶粒重构参数。
3. 双击 `run.bat`。
4. 在 `output` 中获得 `ebsd_base_model.inp` 和 `ebsd_base_model.cae`。
5. 复制基础 CAE，再添加具体分析所需的载荷、边界条件、裂纹和损伤设置。

## Abaqus 插件

双击 `install_plugin.bat`，然后重新启动 Abaqus/CAE。在菜单中打开：

```text
Plug-ins → EBSD2Abaqus...
```

选择 CTF 文件和项目输出文件夹后点击 `Build CAE`。插件会依次调用 MTEX、Python 和 Abaqus noGUI，并在所选项目文件夹的 `output` 子目录生成基础 INP 和 CAE。运行记录保存在 `conversion.log`。

插件安装包位于 `abaqus_plugin/EBSD2Abaqus`，可以随项目一起发布。

## 更换 EBSD 数据

1. 如果需要保留上一次结果，先将 `output` 复制到项目外部；
2. 双击 `clean_output.bat` 清空生成结果；
3. 删除或覆盖 `input/ebsd.ctf`；
4. 将新数据命名为 `ebsd.ctf` 放入 `input`；
5. 如果材料相发生变化，修改 `config.json`；
6. 再次双击 `run.bat`。

`clean_output.bat` 只清理 `output`，不会删除输入数据、配置文件或程序代码。

## 配置说明

- `misorientation_deg`：MTEX 晶粒重构阈值，单位为度；
- `min_grain_pixels`：保留晶粒的最小像素数；
- `coordinate_scale`：从 EBSD 的 μm 坐标转换到模型单位，默认 `0.001`，即转换为 mm；
- `element_type`：二维单元类型，默认 `CPE4`；
- `umat_prefix`、`umat_suffix`：位于三项 Euler 角前后的用户材料常数；
- `depvar_count`：用户材料状态变量数量。

材料常数排列为：

```text
umat_prefix + [phi1, Phi, phi2] + umat_suffix + [equivalent_grain_diameter]
```

如果更换 UMAT，需要同步修改上述常数顺序和 `depvar_count`。

## 项目结构

```text
EBSD2Abaqus/
├─ config.json
├─ run.bat
├─ clean_output.bat
├─ input/
│  └─ ebsd.ctf              # 用户数据，不提交到 Git
├─ output/                   # 自动生成，不提交到 Git
└─ scripts/
   ├─ export_ebsd.m
   ├─ build_inp.py
   └─ import_cae.py
```
