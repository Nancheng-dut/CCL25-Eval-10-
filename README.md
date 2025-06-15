# CCL25-Eval-10-
CCL25-Eval 任务10：细粒度中文仇恨识别评测
model_download文件是用于模型下载，[具体方法参考](https://blog.csdn.net/a61022706/article/details/134887159?ops_request_misc=%257B%2522request%255Fid%2522%253A%25220db84b18cb5c50cda37c71c88a746d93%2522%252C%2522scm%2522%253A%252220140713.130102334..%2522%257D&request_id=0db84b18cb5c50cda37c71c88a746d93&biz_id=0&utm_medium=distribute.pc_search_result.none-task-blog-2~all~ElasticSearch~search_v2-8-134887159-null-null.142^v102^pc_search_result_base3&utm_term=%E6%9C%8D%E5%8A%A1%E5%99%A8%E8%BF%9E%E6%8E%A5huggingface&spm=1018.2226.3001.4187)
lora_hate_recognition是用lora微调训练的文件，
run.py是模型运行文件
Evaluation_lora_recognition.py是一个评估文件，
json_to_txt.py是格式转换，将输出的json文件转换成txt，
具体运行说明如下：
首先通过modeldownload文件下载一个你喜欢的模型，会自动创建一个根目录dataroot，里面会有你下载的模型；然后在终端运行lora文件，可以修改其中的参数和文件路径等，会训练出一个新的目录，里面是lora模型；
然后终端运行run.py，就会根据你输入的测试集输出仇恨识别结果了。json文件的话不用改格式，想要txt文件在运行一下json to txt，就能改成txt格式。
github只让上传25MB以下的文件，原始模型和训练模型都没法上传进来，各位大佬可以参考一下我的方法，自己训练一下，我用的4090显卡，1.7b模型训练两个小时左右，0.6b不到半个小时就可以了，运行的时候输入两千条再输出
也得二十多分钟，可能我确实不是专业做深度学习的hhhhh。
