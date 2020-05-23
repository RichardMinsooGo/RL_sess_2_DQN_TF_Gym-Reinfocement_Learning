import tensorflow as tf
import gym
import numpy as np
import random
from collections import deque
import dqn
from typing import List
import time
import sys

import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
from tensorflow.python.framework import ops
ops.reset_default_graph()

env = gym.make('Pendulum-v0')
# env = env.unwrapped
env.seed(1)

state_size = env.observation_space.shape[0]
action_size = 25

model_path = os.path.join(os.getcwd(), 'save_model')
graph_path = os.path.join(os.getcwd(), 'save_graph')

if not os.path.isdir(model_path):
    os.mkdir(model_path)

if not os.path.isdir(graph_path):
    os.mkdir(graph_path)

discount_factor = 0.99
N_EPISODES = 5000
N_train_result_replay = 20
target_update_cycle = 200
memory_size = 50000
batch_size = 32

ep_step = []
MIN_E = 0.0
EPSILON_DECAYING_EPISODE = N_EPISODES * 0.01

def annealing_epsilon(episode: int, min_e: float, max_e: float, target_episode: int) -> float:

    slope = (min_e - max_e) / (target_episode)
    intercept = max_e

    return max(min_e, slope * episode + intercept)

def Copy_Weights(*, dest_scope_name: str, src_scope_name: str) -> List[tf.Operation]:
    op_holder = []

    src_vars = tf.get_collection(
        tf.GraphKeys.TRAINABLE_VARIABLES, scope=src_scope_name)
    dest_vars = tf.get_collection(
        tf.GraphKeys.TRAINABLE_VARIABLES, scope=dest_scope_name)

    for src_var, dest_var in zip(src_vars, dest_vars):
        op_holder.append(dest_var.assign(src_var.value()))

    return op_holder
                 
def train_model(agent, target_agent, minibatch):
    x_stack = np.empty(0).reshape(0, agent.state_size)
    y_stack = np.empty(0).reshape(0, agent.action_size)

    for state, action, reward, next_state, done in minibatch:
        Q_Global = agent.predict(state)
        
        #terminal?
        if done:
            Q_Global[0,action] = reward
            
        else:
            #Obtain the Q' values by feeding the new state through our network
            Q_Global[0,action] = reward + discount_factor * np.max(target_agent.predict(next_state))

        y_stack = np.vstack([y_stack, Q_Global])
        x_stack = np.vstack([x_stack, state])
    
    return agent.update(x_stack, y_stack)

def main():
    last_n_game_reward = deque(maxlen=30)
    last_n_game_reward.append(-120)
    memory = deque(maxlen=memory_size)

    with tf.Session() as sess:
        agent        = dqn.DQN(sess, state_size, action_size, name="main")
        target_agent = dqn.DQN(sess, state_size, action_size, name="target")
        
        init = tf.global_variables_initializer()
        sess.run(init)
        
        copy_ops = Copy_Weights(dest_scope_name="target",
                                    src_scope_name="main")
        sess.run(copy_ops)
        start_time = time.time()
        step = 0
        episode = 0

        while time.time() - start_time < 60 * 60:
            
            state = env.reset()
            rall = 0
            done = False
            ep_step = 0
            rewards = 0
            e = annealing_epsilon(episode, MIN_E, 1.0, EPSILON_DECAYING_EPISODE)
            progress = " "
            
            while not done :
                ep_step += 1
                step += 1
                
                if step < memory_size:
                    progress = "Exploration"
                else :
                    progress = "Training" 
                
                if e > np.random.rand(1):
                    # action = env.action_space.sample()
                    action = np.random.randint(0, agent.action_size)

                else:
                    actions_value = agent.predict(state)
                    action = np.argmax(actions_value)

                f_action = (action-(action_size-1)/2)/((action_size-1)/4)
                # print(f_action)
                next_state, reward, done, _ = env.step(np.array([f_action]))
                
                reward /= 10
                rewards += reward                
                
                # f_action = np.array((action + env.action_space.high) *(action_size - 1)/4 ) 
                memory.append((state, action, reward, next_state, done))

                if len(memory) > memory_size:
                    memory.popleft()
                    
                state = next_state
                
                if progress == "Training":
                    # for _ in range (batch_size):
                    minibatch = random.sample(memory, batch_size)
                    LossValue,_ = train_model(agent,target_agent, minibatch)
                        
                    if done or ep_step % target_update_cycle == 0:
                        sess.run(copy_ops)
                        
                if done or ep_step == 200:
                    if progress == "Training":
                        episode += 1
                    last_n_game_reward.append(rewards)
                    avg_reward = np.mean(last_n_game_reward)
                    print("Episode :{:>5} / rewards :{:>5.2f} / recent n-game reward :{:>5.2f} / memory length :{:>5}"
                          .format(episode, rewards, avg_reward,len(memory)))
                    
                    break
                        # sys.exit()
            
            if len(last_n_game_reward) == last_n_game_reward.maxlen:
                # avg_reward = np.mean(last_n_game_reward)

                if avg_reward > -15:
                    print("Game Cleared within {:>5} episodes with avg reward {:>5.2f}".format(episode, avg_reward))
                    break
            

        for episode in range(N_train_result_replay):
            
            state = env.reset()
            done = False
            ep_step = 0
            rewards = 0
            
            while not done :
                env.render()
                ep_step += 1
                Q_Global = agent.predict(state)
                action = np.argmax(Q_Global)
                
                f_action = (action-(action_size-1)/2)/((action_size-1)/4)
                # print(f_action)
                next_state, reward, done, _ = env.step(np.array([f_action]))
                
                reward /= 10
                rewards += reward
                state = next_state

            print("Episode : {:>5} rewards :{:>5.2f} ".format(episode+1, rewards))

if __name__ == "__main__":
    main()