功能：
读取一个文件夹下所有文件，目前文件类型有.pdf	.html	.xlsx	.xls	.doc	.docx这六种
针对两种文件类型（报告类：pdf、docx、doc、html；表格类：xlsx、xls），分别调用不同的函数进行处理
输入是文件夹的路径，输出是这个文件夹下所有文件的内容（句子列表）
输出内容需要是句子列表（按照中文句号等分割）



1. 初始化——第一次运行即可：folder_preprocess: 删除非指定类型文件、解压删除压缩文件、删除特定文件、删除空文件、删除空文件夹、分类文件夹
2. report_read: 读取报告类文件，输入是文件夹路径，返回句子列表，可选参数有convert_doc
3. table_read: 读取表格类文件，输入是文件夹路径，返回句子列表，可选参数有convert_doc
4. report_trans_table：将某些报表类pdf转为excel
5. folder_read: 读取文件夹下所有文件，输入是num（目标模板的行数），返回句子列表
6. util文件夹：
   （1）工具类，其中target_excel_label_list：读取目标模板的数据存到静态变量中


todo: report_trans_table和table_read有问题，存在着转换后的excel，在table_read中无法读取


运行：
1. 初始化：folder_preprocess(folder_path)
2. keyword_match()：得到第一次的匹配结果