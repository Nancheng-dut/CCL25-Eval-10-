import torch
import json
torch.cuda.set_device(0)  # 强制使用 cuda:0
from transformers import AutoModelForCausalLM, AutoTokenizer, DataCollatorForSeq2Seq
from peft import LoraConfig, get_peft_model, TaskType,  PrefixTuningConfig

#----------------------------------------加载模型-------------------------------------------#
model_name = "./dataroot/models/Qwen/Qwen3-1.7B"
# 确定设备
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
#print('device:', device)
tokenizer = AutoTokenizer.from_pretrained(model_name,
                                          trust_remote_code=True,
                                          local_files_only=True)

base_model = AutoModelForCausalLM.from_pretrained(model_name,
                                             device_map="auto",
                                             torch_dtype="auto",
                                             local_files_only=True)

#model.to(device)

print('原模型加载完毕')
#----------------------------------------加载模型-------------------------------------------#


# 替换 PrefixTuningConfig 为 LoRAConfig
peft_config = LoraConfig(
    task_type=TaskType.CAUSAL_LM,
    inference_mode=False,
    r=8,  # LoRA的秩
    lora_alpha=32,  # 缩放系数
    lora_dropout=0.1,  # Dropout率
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj"]  # 针对Qwen的目标模块
)

model = get_peft_model(base_model, peft_config)
model.print_trainable_parameters()  # 预期约4.2M可训练参数

#---------------------------------配置Qwen3-0.6b微调参数-------------------------------------#

#-------------------------------定义采用已训练好的模型推理函数-------------------------------------#
def generate_response(prompt, model):
    inputs = tokenizer(prompt, return_tensors="pt", max_length=1024, truncation=True).to(device)

    with torch.no_grad():
        outputs = model.generate(
            input_ids=inputs.input_ids,
            attention_mask=inputs.attention_mask,
            max_new_tokens=256,
            do_sample=True,
            top_p=0.9,
            temperature=0.2,
            pad_token_id=tokenizer.eos_token_id
        )

    response = tokenizer.decode(outputs[0][len(inputs.input_ids[0]):], skip_special_tokens=True)
    return response.split("\n")[0].strip()  # 取第一个换行前的部分
#-------------------------------定义采用已训练好的模型推理函数-------------------------------------#

from datasets import load_dataset
# 加载完整数据集
train_dataset = load_dataset("json", data_files=r"train_with_instruction.json")["train"]
test_dataset = load_dataset("json", data_files=r"test1_with_instruction.json")["train"]
print('data length',len(train_dataset))
# 选择前1000条数据
#dataset = full_dataset.select(range(8000))  # 索引0-5000
dataset = train_dataset
def process_func(example):
    MAX_LENGTH = 1024
    # 将prompt进行tokenize，这里我们没有利用tokenizer进行填充和截断
    # 这里我们自己进行截断，在DataLoader的collate_fn函数中进行填充
    instruction = tokenizer(example["instruction"] + "\n\n我需要你进行类似上述处理的句子是:" +
        example["content"] + "\n\n")
    # 将output进行tokenize，注意添加eos_token
    response = tokenizer(example["output"] + tokenizer.eos_token)
    # 将instruction + output组合为input
    input_ids = instruction["input_ids"] + response["input_ids"]
    attention_mask = instruction["attention_mask"] + response["attention_mask"]
    # prompt设置为-100,不计算loss
    labels = [-100] * len(instruction["input_ids"]) + response["input_ids"]
    # 设置最大长度，进行截断
    if len(input_ids) > MAX_LENGTH:
        input_ids = input_ids[:MAX_LENGTH]
        attention_mask = attention_mask[:MAX_LENGTH]
        labels = labels[:MAX_LENGTH]
    return {
        "input_ids": input_ids,
        "attention_mask": attention_mask,
        "labels": labels
    }

train_dataset = dataset.map(process_func, remove_columns=dataset.column_names)
# 加载测试数据集
test_dataset = test_dataset.select(range(10, 11)).map(
    lambda example: {
        "prompt": example["instruction"] + "\n\n我需要你进行类似上述处理的句子是:" +
        example["content"] + "\n\n",
        "ground_truth": example["id"]
    },
    remove_columns=test_dataset.column_names
)
print('dataset down',f'current strcture:{train_dataset}')
# 展示两条数据
print(train_dataset[:2])
# 解码一条数据验证预处理是否成功
print(tokenizer.decode(train_dataset[1]["input_ids"]))
print(tokenizer.decode(list(filter(lambda x: x != -100, train_dataset[1]["labels"]))))


#---------------------------------Baseline model inference---------------------------------------#
results = []
for example in test_dataset:
    prompt = example["prompt"]
    ground_truth = example["ground_truth"]

    generated = generate_response(prompt, base_model)

    results.append({
        "input": prompt.split("Assistant:")[0].strip(),
        "generated": generated,
        "ground_truth": ground_truth
    })

# 打印前5个结果示例
for i, res in enumerate(results[:5]):
    print(f"### 示例 {i + 1}")
    print(f"[输入]\n{res['input']}")
    print(f"[生成结果]\n{res['generated']}")
    print(f"[参考答案]\n{res['ground_truth']}")
    print("\n" + "=" * 50 + "\n")

with open("base_results.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
#---------------------------------Baseline model inference---------------------------------------#

#---------------------------------LoRA训练开始---------------------------------------#
from transformers import DefaultDataCollator

data_collator = DefaultDataCollator()

from transformers import TrainingArguments, Trainer

training_args = TrainingArguments(
    output_dir="my_qwen_qa_model",
    num_train_epochs=1,  # 训练的总轮数
    per_device_train_batch_size=4,  # 每个设备上的训练批次大小
    gradient_accumulation_steps=8,  # 梯度累积步数，在进行反向传播前累积多少步
    save_strategy="epoch",  # 保存策略，每个 epoch 保存一次模型
    learning_rate=5e-4,  # 学习率
    fp16=True,  # 启用 16 位浮点数训练，提高训练速度并减少显存使用
    logging_dir='./logs',  # 日志保存目录
    logging_steps=50,
    dataloader_pin_memory=False,  # 禁用 pin_memory 以节省内存
)


trainer = Trainer(
    model=model,    # 预训练模型
    args=training_args,      # 训练参数
    train_dataset=train_dataset,  # 训练集
    data_collator=DataCollatorForSeq2Seq(tokenizer=tokenizer, padding=True)
)

trainer.train()


print('训练完毕')

# 创建保存模型的目录
import os
import json
save_directory = 'Qwen3-1.7B-LoRA-Racism'
os.makedirs(save_directory, exist_ok=True)

# 合并LoRA权重到基础模型
#model = model.merge_and_unload()

# 保存完整模型（包含LoRA合并后的权重）
model.save_pretrained(save_directory)
tokenizer.save_pretrained(save_directory)

# 将配置文件下载到模型目录中
config = model.config.to_dict()
config_path = os.path.join(save_directory, 'config.json')
with open(config_path, 'w') as f:
    json.dump(config, f, ensure_ascii=False, indent=4)

print(f"Model and configuration saved to {save_directory}")
#---------------------------------LoRA训练开始---------------------------------------#

#---------------------------------测试LoRA的训练效果---------------------------------------#
from peft import PeftModel

# 正确加载 LoRA 模型（需先加载基础模型）
base_model = AutoModelForCausalLM.from_pretrained(model_name, device_map="auto")
loaded_model = PeftModel.from_pretrained(base_model, save_directory).to(device)
loaded_model = loaded_model.merge_and_unload()  # 关键步骤：合并 LoRA 权重


# 执行测试
results = []
for example in test_dataset:
    prompt = example["prompt"]
    ground_truth = example["ground_truth"]

    generated = generate_response(prompt, loaded_model)

    results.append({
        "input": prompt.split("Assistant:")[0].strip(),
        "generated": generated,
        "ground_truth": ground_truth
    })

# 打印前5个结果示例
for i, res in enumerate(results[:5]):
    print(f"### 示例 {i + 1}")
    print(f"[输入]\n{res['input']}")
    print(f"[生成结果]\n{res['generated']}")
    print(f"[参考答案]\n{res['ground_truth']}")
    print("\n" + "=" * 50 + "\n")

with open("test_results.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
#---------------------------------测试LoRA的训练效果---------------------------------------#
